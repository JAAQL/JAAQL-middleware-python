from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import execute_supplied_statement_singleton, execute_supplied_statement
from jaaql.mvc.queries import QUERY__load_application_configuration, QUERY__load_application_configurations
from jaaql.constants import KEY__application, KEY__configuration, KEY__artifact_base_uri, FILE__canned_queries
from jaaql.utilities.utils_no_project_imports import load_artifact
from jaaql.exceptions.http_status_exception import HttpStatusException
from requests.exceptions import RequestException
import json

ERR__invalid_query = "Could not find the canned query that you have specified! Could not find %s"


class CachedCannedQueryService:

    def __init__(self, is_container: bool, connection: DBInterface):
        self.canned_queries = {}
        # self.init_canned_queries(is_container, connection)

    def init_canned_queries(self, is_container: bool, connection: DBInterface):
        configs = execute_supplied_statement(connection, QUERY__load_application_configurations, as_objects=True)
        for config in configs:
            self.refresh_configuration(is_container, connection, config[KEY__application], config[KEY__configuration],
                                       config[KEY__artifact_base_uri])

    def get_canned_query(self, application: str, configuration: str, file: str, pos: int) -> str:
        if application not in self.canned_queries:
            raise HttpStatusException(ERR__invalid_query % "application")

        if configuration not in self.canned_queries[application]:
            raise HttpStatusException(ERR__invalid_query % "configuration")

        queries = self.canned_queries[application][configuration]

        if file not in queries:
            raise HttpStatusException(ERR__invalid_query % "file")

        if pos not in queries[file]:
            raise HttpStatusException(ERR__invalid_query % "pos")

        return queries[file][pos]

    def refresh_configuration(self, is_container: bool, connection: DBInterface, application: str, configuration: str,
                              config_resource_url: str = None):
        if config_resource_url is None:
            config_resource_url = execute_supplied_statement_singleton(connection, QUERY__load_application_configuration,
                                                                       {KEY__application: application, KEY__configuration: configuration},
                                                                       as_objects=True)[KEY__artifact_base_uri]

        canned_queries = None
        try:
            canned_queries = load_artifact(is_container, config_resource_url, FILE__canned_queries)
            json.loads(canned_queries)
        except FileNotFoundError:
            pass  # No canned queries for app. This is _okay_
        except RequestException:
            pass  # Same as above

        if application not in canned_queries:
            self.canned_queries[application] = {}

        if configuration not in canned_queries[application]:
            self.canned_queries[application][configuration] = {}

        self.canned_queries[application][configuration] = canned_queries

        # TODO broadcast this to other workers
