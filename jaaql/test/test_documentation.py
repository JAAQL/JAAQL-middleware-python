"""
JAAQL builds the OpenAPI documentation of every route at boot, once the controller has routed them (jaaql.create_app), as data dumped by
yaml.safe_dump (jaaql/openapi/swagger_documentation.py), and writes it as YAML, as JSON and as a Swagger UI page. Every text in it (a
description, a summary, a name, an example) is a string of the YAML whatever it holds: ': ', '#', a leading '-', quotes or a line break
broke the hand-built YAML before (5.3.23: a description with ': ' in it stopped every worker before it served a request), and a text YAML
reads as something else ("yes", "123", a date) is still that text; an example that is a number or a flag keeps its type.

    python -m unittest jaaql.test.test_documentation
"""
import json
import os
import tempfile
import types
import unittest
from unittest import mock

import yaml

import jaaql.documentation as documentation
from jaaql.constants import ENVIRON__sentinel_url
from jaaql.jaaql import dir_non_builtins
from jaaql.mvc.controller import JAAQLController
from jaaql.openapi.swagger_documentation import produce_all_documentation, documentation_of, dump_documentation, SwaggerDocumentation, \
    SwaggerMethod, SwaggerArgumentResponse, SwaggerResponse, SwaggerFlatResponse, SwaggerResponseException, SwaggerList, SwaggerException, \
    REST__GET, REST__POST, ARG_RESP__allow_all, RESPONSE__200_ok
from jaaql.test.test_slow_queries import StubModel

URL = "http://127.0.0.1/api/"

# Each broke the hand-built YAML or came back from it as something else than the text it was
TEXTS = [
    "a description: with a colon and a space", "Answered 503 with Retry-After: 5", "a # that started a comment", "#leading hash",
    "- a leading dash", "-", ": leading colon", "? a leading question mark", "* an alias", "& an anchor", "! a tag", "% a directive",
    "@ reserved", "` reserved", "| a literal", "> a folded", "{ a flow mapping", "[ a flow list", "a, b", "'single quoted'",
    '"double quoted"', 'a "quote" inside', "it's", "a back\\slash", "\\n not a new line", "a line\nand another", "a\ttab",
    " leading and trailing spaces ", "trailing colon:", "yes", "no", "on", "off", "true", "False", "null", "~", "None", "123", "1.5",
    "0x1F", "1e3", "2026-11-18", "2026-11-18 12:00:00", "=", "<<", "é and ü and 日本", "an emoji 🎉", "</script><script>alert(1)</script>",
    "%s and %d", "{application}", "",
]


def hazard_documentation_module(texts=TEXTS):
    """
    A documentation module as a project supplies one, whose route's texts (descriptions, summary, tag, examples, an exception's message) and
    names are every text of texts
    """
    def text(idx):
        return texts[idx % len(texts)]

    module = types.ModuleType("documentation_hazards")
    module.TITLE = "Hazards: a title </title> & more"
    module.DESCRIPTION = "Description: " + text(0)
    module.FILENAME = "hazards"
    module.VERSION = "1.0"
    fields = [SwaggerArgumentResponse(name="field_%d" % idx, description=text, arg_type=str, example=[text if text else "empty"])
              for idx, text in enumerate(texts)]
    module.DOCUMENTATION__hazards = SwaggerDocumentation(
        tags="Tag: with a colon",
        security=False,
        methods=[
            SwaggerMethod(
                name="Summary: " + text(1),
                description="\n".join(texts),
                method=REST__GET,
                arguments=[SwaggerArgumentResponse(name="argument_%d" % idx, description=text, arg_type=str, example=[text if text else "e"])
                           for idx, text in enumerate(texts)] + [
                    SwaggerArgumentResponse(name="number", description="A number: 5", arg_type=int, example=[5]),
                    SwaggerArgumentResponse(name="flag", description="A flag: true", arg_type=bool, example=[True]),
                    SwaggerArgumentResponse(name="ratio", description="A ratio: 1.5", arg_type=float, example=[1.5])
                ],
                response=SwaggerFlatResponse(description="Flat: answered", body="yes: a body"),
                exceptions=[SwaggerResponseException(code=400, message="Bad: " + text(2)),
                            SwaggerResponseException(code=500, message="- " + text(3))]
            ),
            SwaggerMethod(
                name="Posted: " + text(4),
                description=text(5),
                method=REST__POST,
                body=fields + [
                    SwaggerArgumentResponse(name="nested: list", description="A list: of fields", arg_type=SwaggerList(
                        SwaggerArgumentResponse(name="inner", description="Inner: # text", arg_type=str, example=["123"]))),
                    SwaggerArgumentResponse(name="anything", description="Anything: at all", arg_type=ARG_RESP__allow_all)
                ],
                response=SwaggerResponse(description="Answered: " + text(6), response=[
                    SwaggerArgumentResponse(name="answer", description="Answer: 'quoted'", arg_type=str, example=["no"])
                ])
            )
        ]
    )
    module.DOCUMENTATION__hazards.path = "/hazards/<application>"
    return module


class TestDocumentation(unittest.TestCase):

    def setUp(self):
        env = {k: v for k, v in os.environ.items() if k != ENVIRON__sentinel_url}
        with mock.patch.dict(os.environ, env, clear=True):
            self.controller = JAAQLController(StubModel(), True, "http+unix://%2Ftmp%2Fjaaql.sock")
        self.controller.create_app()

    def produced(self, modules, is_prod):
        # What produce_all_documentation writes for modules: each file's YAML (parsed) and JSON, by file name without its extension
        with tempfile.TemporaryDirectory() as base_path:
            produce_all_documentation(modules, URL, is_prod=is_prod, base_path=base_path)
            folder = os.path.join(base_path, "swagger")
            written = {}
            for name in sorted(os.listdir(folder)):
                stem, extension = os.path.splitext(name)
                with open(os.path.join(folder, name), encoding="utf-8") as file:
                    written.setdefault(stem, {})[extension] = file.read()
            return written

    def test_every_route_documents_at_boot(self):
        with tempfile.TemporaryDirectory() as base_path:
            produce_all_documentation(dir_non_builtins(documentation), URL, is_prod=True, base_path=base_path)
            self.assertTrue(any(files for _, _, files in os.walk(base_path)))

    def test_every_routes_documentation_round_trips_through_a_yaml_parser(self):
        modules = dir_non_builtins(documentation)
        for is_prod in (True, False):
            written = self.produced(modules, is_prod)
            self.assertEqual({"jaaql_api", "jaaql_internal_api"}, set(written))
            for module in modules:
                document = documentation_of(module, URL, is_prod)
                if document is None:
                    continue
                files = written[module.FILENAME]
                with self.subTest(module.__name__, is_prod=is_prod):
                    self.assertEqual(document, yaml.safe_load(dump_documentation(document)))
                    self.assertEqual(document, yaml.safe_load(files[".yaml"]))
                    self.assertEqual(document, json.loads(files[".json"]))
                    self.assertEqual(json.dumps(document), files[".json"])
                docs = [value for value in vars(module).values() if isinstance(value, SwaggerDocumentation)]
                self.assertNotEqual([], docs)
                parsed = yaml.safe_load(files[".yaml"])["paths"]
                for doc in docs:
                    path = doc.path.replace("<", "{").replace(">", "}")
                    for method in doc.methods:
                        with self.subTest(module.__name__, path=path, method=method.method, is_prod=is_prod):
                            operation = parsed[path][method.method.lower()]
                            self.assertEqual(method.description, operation["description"])
                            self.assertEqual(method.name, operation["summary"])
                            self.assertIn("200", operation["responses"])

    def test_texts_yaml_would_misread_come_back_as_they_are(self):
        module = hazard_documentation_module()
        written = self.produced([module], False)["hazards"]
        parsed = yaml.safe_load(written[".yaml"])
        self.assertEqual(parsed, json.loads(written[".json"]))
        self.assertEqual(documentation_of(module, URL), parsed)
        self.assertEqual(module.TITLE, parsed["info"]["title"])
        self.assertEqual(module.DESCRIPTION, parsed["info"]["description"])
        self.assertEqual("1.0", parsed["info"]["version"])
        get, post = parsed["paths"]["/hazards/{application}"]["get"], parsed["paths"]["/hazards/{application}"]["post"]
        self.assertEqual(["Tag: with a colon"], get["tags"])
        self.assertEqual("Summary: " + TEXTS[1], get["summary"])
        self.assertEqual("\n".join(TEXTS), get["description"])
        arguments = {parameter["name"]: parameter for parameter in get["parameters"]}
        for idx, text in enumerate(TEXTS):
            with self.subTest(text=text):
                self.assertEqual(text, arguments["argument_%d" % idx]["description"])
                self.assertEqual(text if text else "e", arguments["argument_%d" % idx]["example"])
                self.assertIs(True, arguments["argument_%d" % idx]["required"])
                self.assertEqual("query", arguments["argument_%d" % idx]["in"])
                schema = post["requestBody"]["content"]["application/json"]["schema"]
                self.assertEqual(text, schema["properties"]["field_%d" % idx]["description"])
                self.assertEqual(text if text else "empty", schema["example"]["field_%d" % idx])
        self.assertEqual((5, True, 1.5), (arguments["number"]["example"], arguments["flag"]["example"], arguments["ratio"]["example"]))
        self.assertEqual({"type": "integer"}, arguments["number"]["schema"])
        self.assertEqual("yes: a body", get["responses"]["200"]["content"]["application/json"]["schema"]["example"])
        self.assertEqual({"200", "400", "500"}, set(get["responses"]))
        self.assertEqual("Bad: " + TEXTS[2], get["responses"]["400"]["description"])
        self.assertEqual("- " + TEXTS[3], get["responses"]["500"]["description"])
        schema = post["requestBody"]["content"]["application/json"]["schema"]
        self.assertEqual([{"inner": "123"}], schema["example"]["nested: list"])
        self.assertEqual({}, schema["example"]["anything"])
        self.assertEqual("Inner: # text", schema["properties"]["nested: list"]["items"]["properties"]["inner"]["description"])
        self.assertEqual(["field_%d" % idx for idx in range(len(TEXTS))] + ["nested: list", "anything"], schema["required"])
        answered = post["responses"]["200"]
        self.assertEqual("Answered: " + TEXTS[6], answered["description"])
        self.assertEqual({"answer": "no"}, answered["content"]["application/json"]["schema"]["example"])
        # The page shows the title as text, and its script holds the document whole
        self.assertIn("Swagger UI - Hazards: a title &lt;/title&gt; &amp; more</title>", written[".html"])
        self.assertNotIn("</script><script>alert(1)", written[".html"])
        spec = written[".html"].split("spec: ", 1)[1]
        self.assertEqual(parsed, json.JSONDecoder().raw_decode(spec)[0])

    def test_a_method_that_declares_no_200_answers_200_ok_once_documented(self):
        # As create_app's produce_all_documentation leaves it at boot, which the routes rely on (BaseJAAQLController.get_response)
        module = hazard_documentation_module(["text"])
        method = module.DOCUMENTATION__hazards.methods[0]
        method.responses = [SwaggerFlatResponse(description="Created", code=201, body="made")]
        self.produced([module], True)
        self.assertEqual([201, 200], [response.code for response in method.responses])
        self.assertEqual(RESPONSE__200_ok, method.responses[-1].description)
        self.produced([module], True)
        self.assertEqual(2, len(method.responses))

    def test_a_production_document_leaves_out_what_is_local_only(self):
        module = hazard_documentation_module(["text"])
        method = module.DOCUMENTATION__hazards.methods[0]
        method.arguments.append(SwaggerArgumentResponse(name="local", description="Local: only", arg_type=str, example=["x"],
                                                        local_only=True))
        names = {is_prod: [parameter["name"] for parameter in documentation_of(module, URL, is_prod)["paths"]["/hazards/{application}"]
                           ["get"]["parameters"]] for is_prod in (True, False)}
        self.assertNotIn("local", names[True])
        self.assertIn("local", names[False])

    def test_a_list_among_the_fields_of_an_example_is_refused(self):
        # The hand-built YAML of one could not be parsed; an example is either a list or fields
        module = hazard_documentation_module(["text"])
        module.DOCUMENTATION__hazards.methods[1].body.append(SwaggerList(
            SwaggerArgumentResponse(name="listed", description="Listed", arg_type=str, example=["x"])))
        with self.assertRaises(SwaggerException):
            documentation_of(module, URL)


if __name__ == "__main__":
    unittest.main()
