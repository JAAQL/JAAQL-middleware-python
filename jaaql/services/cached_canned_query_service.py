from jaaql.db.db_interface import DBInterface
from jaaql.db.db_utils import execute_supplied_statement_singleton, execute_supplied_statement
from jaaql.constants import KEY__application, FILE__canned_queries
from jaaql.utilities.utils_no_project_imports import load_template
from jaaql.exceptions.http_status_exception import HttpStatusException
from requests.exceptions import RequestException
import json

ERR__invalid_query = "Could not find the canned query that you have specified! Could not find %s"


class CachedCannedQueryService:

    def __init__(self, is_container: bool, connection: DBInterface):
        self.canned_queries = {}
        # self.init_canned_queries(is_container, connection)

    def init_canned_queries(self, is_container: bool, connection: DBInterface):
        pass
        # TODO disabled for now
        # apps = execute_supplied_statement(connection, QUERY__load_application, as_objects=True)
        # for app in apps:
        #     self.refresh_application(is_container, connection, app[KEY__name], app[KEY__templates_source])

    def get_canned_query(self, application: str, file: str, pos: int) -> str:
        if application not in self.canned_queries:
            raise HttpStatusException(ERR__invalid_query % "application")

        queries = self.canned_queries[application]

        if file not in queries:
            raise HttpStatusException(ERR__invalid_query % "file")

        if pos not in queries[file]:
            raise HttpStatusException(ERR__invalid_query % "pos")

        return queries[file][pos]

    def refresh_application(self, is_container: bool, connection: DBInterface, application: str, config_resource_url: str = None):
        pass
        # TODO implement in future
        # if config_resource_url is None:
        #     config_resource_url = execute_supplied_statement_singleton(connection, QUERY__load_applications,
        #                                                                {KEY__application: application},
        #                                                                as_objects=True)[KEY__template_base_url]
#
        # canned_queries = None
        # try:
        #     canned_queries = load_template(is_container, config_resource_url, FILE__canned_queries)
        #     json.loads(canned_queries)
        # except FileNotFoundError:
        #     pass  # No canned queries for app. This is _okay_
        # except RequestException:
        #     pass  # Same as above
#
        # if application not in canned_queries:
        #     self.canned_queries[application] = {}
#
        # self.canned_queries[application] = canned_queries
#
        # TODO broadcast this to other workers
