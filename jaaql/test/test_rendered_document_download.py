"""
A rendered document that is no file (POST /documents with create_file false) is downloaded from GET /rendered_documents, once, under the
name its render gave it (document_request.file_name), inline or, with as_attachment, as an attachment. The download deletes the document,
so a second one finds none.

    python -m unittest jaaql.test.test_rendered_document_download

Needs only the package's requirements, as jaaql.test.test_server_errors: JAAQL's lookup connection is a stand-in database interface
holding the document_request rows
"""
import unittest
from datetime import datetime, timezone
from unittest import mock

from jaaql.mvc.model import JAAQLModel
from jaaql.test.test_server_errors import ServerErrorCase
from jaaql.test.test_slow_queries import TimedInterface

RENDERED_DOCUMENTS = "/rendered_documents"
DOCUMENT_ID = "b47dc954-d608-4e1b-8a8c-d8b754ee554b"
CONTENT = b"%PDF-1.7\n% a synthetic rendered document\n%%EOF\n"
FETCH_COLUMNS = ["base_url", "document_id", "render_as", "file_name", "create_file", "completed", "oauth_token"]


class Documents(TimedInterface):
    """
    JAAQL's lookup connection holding document_request rows, rows giving each uuid its content, all rendered and none a file: answers
    the statements a download runs (the document's row, then DELETE ... RETURNING content) and keeps the start of each
    """

    def __init__(self, rows=None, file_name="invoice-2026-11.pdf"):
        super().__init__()
        self.rows = dict(rows if rows is not None else {DOCUMENT_ID: CONTENT})
        self.file_name = file_name
        self.statements = []

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None, capture_timing=None):
        self.statements.append(" ".join(query.split()[:3]))
        content = self.rows.get(str((parameters or {}).get("document_id")))
        if query.startswith("SELECT app.base_url"):
            return FETCH_COLUMNS, [0] * len(FETCH_COLUMNS), [] if content is None else [[
                "https://lesbij.example", DOCUMENT_ID, "pdf", self.file_name, False, datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc), None]]
        if query.startswith("DELETE FROM document_request"):
            self.rows.pop(str(parameters["document_id"]), None)
        return ["content"], [0], [] if content is None else [[content]]


class TestRenderedDocumentDownload(ServerErrorCase):

    def setUp(self):
        super().setUp()
        self.documents = Documents()
        self.model.jaaql_lookup_connection = self.documents
        self.real = mock.patch.object(self.model, "fetch_document_stream", create=True,
                                      side_effect=lambda inputs, **kwargs: JAAQLModel.fetch_document_stream(self.model, inputs, **kwargs))
        self.real.start()

    def tearDown(self):
        self.real.stop()
        super().tearDown()

    def download(self, as_attachment=None, method="GET"):
        query = {"document_id": DOCUMENT_ID}
        if as_attachment is not None:
            query["as_attachment"] = as_attachment
        return self.client.open(RENDERED_DOCUMENTS, method=method, query_string=query, headers={"User-Agent": "Mozilla/5.0 (Test)"})

    def test_a_rendered_document_downloads_once_under_its_own_name(self):
        res = self.download()
        self.assertEqual((200, CONTENT), (res.status_code, res.get_data()))
        self.assertEqual("application/pdf", res.headers["Content-Type"])
        self.assertEqual("inline; filename=invoice-2026-11.pdf", res.headers["Content-Disposition"])
        self.assertEqual(str(len(CONTENT)), res.headers["Content-Length"])
        self.assertEqual(["SELECT app.base_url, rd.uuid", "DELETE FROM document_request"], self.documents.statements)
        self.assertEqual({}, self.documents.rows)
        # Deleted by the download
        again = self.download()
        self.assertEqual((422, b"Document id not found"), (again.status_code, again.get_data()))
        self.assertEqual([], self.lines())
        self.assertNoReport()

    def test_as_an_attachment(self):
        res = self.download(as_attachment="true")
        self.assertEqual((200, CONTENT), (res.status_code, res.get_data()))
        self.assertEqual("attachment; filename=invoice-2026-11.pdf", res.headers["Content-Disposition"])

    def test_a_name_beyond_ascii_is_given_as_rfc_5987_asks(self):
        self.documents.file_name = "factuur-café.pdf"
        res = self.download(as_attachment="true")
        self.assertEqual((200, CONTENT), (res.status_code, res.get_data()))
        self.assertEqual("attachment; filename=factuur-cafe.pdf; filename*=UTF-8''factuur-caf%C3%A9.pdf", res.headers["Content-Disposition"])


if __name__ == "__main__":
    unittest.main()
