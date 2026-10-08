import os
import tempfile
import unittest
from unittest import mock

import jaaql.documentation as documentation
from jaaql.constants import ENVIRON__sentinel_url
from jaaql.jaaql import dir_non_builtins
from jaaql.mvc.controller import JAAQLController
from jaaql.openapi.swagger_documentation import produce_all_documentation
from jaaql.test.test_slow_queries import StubModel


class TestDocumentation(unittest.TestCase):
    """
    JAAQL builds and parses the OpenAPI documentation of every route at boot, once the controller has routed them (jaaql.create_app); a
    description its hand-built YAML cannot hold, such as one with ': ' in it, stops every worker before it serves a request
    """

    def test_every_route_documents_at_boot(self):
        env = {k: v for k, v in os.environ.items() if k != ENVIRON__sentinel_url}
        with mock.patch.dict(os.environ, env, clear=True):
            controller = JAAQLController(StubModel(), True, "http+unix://%2Ftmp%2Fjaaql.sock")
        controller.create_app()
        with tempfile.TemporaryDirectory() as base_path:
            produce_all_documentation(dir_non_builtins(documentation), "http://127.0.0.1/api/", is_prod=True, base_path=base_path)
            self.assertTrue(any(files for _, _, files in os.walk(base_path)))


if __name__ == "__main__":
    unittest.main()
