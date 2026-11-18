"""
A rendered document that is no file (POST /documents with create_file false) is downloaded from GET /rendered_documents, once, under the
name its render gave it (document_request.file_name), inline or, with as_attachment, as an attachment. The download deletes the document,
so a second one finds none. A HEAD answers the download's status and headers without the document and leaves it to be downloaded.

    python -m unittest jaaql.test.test_rendered_document_download

Needs only the package's requirements, as jaaql.test.test_server_errors: JAAQL's lookup connection is a stand-in database interface
holding the document_request rows
"""
import json
import unittest
from datetime import datetime, timezone
from unittest import mock

from jaaql.mvc.model import JAAQLModel
from jaaql.test.test_server_errors import ServerErrorCase, SUPER_KEY
from jaaql.test.test_slow_queries import TimedInterface
from monitor.main import HEADER__security_bypass

RENDERED_DOCUMENTS = "/rendered_documents"
DOCUMENT_ID = "b47dc954-d608-4e1b-8a8c-d8b754ee554b"
CONTENT = b"%PDF-1.7\n% a synthetic rendered document\n%%EOF\n"
FETCH_COLUMNS = ["base_url", "document_id", "render_as", "file_name", "create_file", "completed", "oauth_token"]


class Documents(TimedInterface):
    """
    JAAQL's lookup connection holding document_request rows, rows giving each uuid its content, all rendered and none a file: answers
    the statements a download runs (the document's row, then DELETE ... RETURNING content, or for a HEAD SELECT content) and keeps the
    start of each
    """

    def __init__(self, rows=None, file_name="invoice-2026-11.pdf"):
        super().__init__()
        self.rows = dict(rows if rows is not None else {DOCUMENT_ID: CONTENT})
        self.file_name = file_name
        self.statements = []
        self.completed = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)

    def execute_query(self, conn, query, parameters=None, wait_hook=None, prepare=False, capture_provenance=None, capture_timing=None):
        self.statements.append(" ".join(query.split()[:3]))
        content = self.rows.get(str((parameters or {}).get("document_id")))
        if query.startswith("SELECT app.base_url"):
            return FETCH_COLUMNS, [0] * len(FETCH_COLUMNS), [] if content is None else [[
                "https://lesbij.example", DOCUMENT_ID, "pdf", self.file_name, False, self.completed, None]]
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
        self.assertEqual((404, 1030, "Document id not found"), (again.status_code, json.loads(again.get_data())["error_code"],
                                                                json.loads(again.get_data())["message"]))
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

    def test_a_head_answers_as_the_download_and_leaves_the_document(self):
        head = self.download(method="HEAD")
        self.assertEqual((200, b""), (head.status_code, head.get_data()))
        self.assertEqual(["SELECT app.base_url, rd.uuid", "SELECT content FROM"], self.documents.statements)
        self.assertEqual({DOCUMENT_ID: CONTENT}, self.documents.rows)
        self.assertEqual(head.status_code, self.download(method="HEAD").status_code)
        got = self.download()
        self.assertEqual((200, CONTENT), (got.status_code, got.get_data()))
        self.assertEqual(sorted(got.headers.items()), sorted(head.headers.items()))
        self.assertEqual({}, self.documents.rows)
        self.assertEqual([], self.lines())
        self.assertNoReport()

    def test_a_document_still_rendering_or_not_there_is_answered_as_documented(self):
        # 425 and 404, as GET /documents documents them. Up to 5.3.30 a download of a document still rendering was answered 500 and
        # reported (Exception: Response with code '425' was not expected, as the route documented no 425), and an id not found 422 on
        # both routes
        documents_get = mock.patch.object(self.model, "fetch_document", create=True,
                                          side_effect=lambda inputs, response: JAAQLModel.fetch_document(self.model, inputs, response))
        with documents_get:
            self.documents.completed = None
            for route in [RENDERED_DOCUMENTS, "/documents"]:
                with self.subTest(route):
                    res = self.client.get(route, query_string={"document_id": DOCUMENT_ID}, headers={HEADER__security_bypass: SUPER_KEY})
                    self.assertEqual((425, 1033, "Document still rendering"), (res.status_code, json.loads(res.get_data())["error_code"],
                                                                              json.loads(res.get_data())["message"]))
            self.assertEqual({DOCUMENT_ID: CONTENT}, self.documents.rows)
            self.documents.rows.clear()
            for route in [RENDERED_DOCUMENTS, "/documents"]:
                with self.subTest(route):
                    res = self.client.get(route, query_string={"document_id": DOCUMENT_ID}, headers={HEADER__security_bypass: SUPER_KEY})
                    self.assertEqual((404, 1030, "Document id not found"), (res.status_code, json.loads(res.get_data())["error_code"],
                                                                           json.loads(res.get_data())["message"]))
        self.assertEqual([], self.lines())
        self.assertNoReport()


if __name__ == "__main__":
    unittest.main()
