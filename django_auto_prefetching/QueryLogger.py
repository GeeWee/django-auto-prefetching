import traceback
from contextlib import contextmanager

from django.db import connection


@contextmanager
def log_queries():
    ql = QueryLogger()
    with connection.execute_wrapper(ql):
        yield
    ql.print_queries()
    ql.print_stats()

class QueryLogger:
    """
    QueryLogger that logs all queries and their callstack. Useful for debugging
    where queries are made, when performance-tuning
    """

    def __init__(self):
        self.queries = []

    def __call__(self, execute, sql, params, many, context):
        caller = self.get_traceback(limit=5, ignore_modules=["django/db/", "debug_toolbar"])

        self.queries.append({"sql": sql, "caller": caller})
        execute(sql, params, many, context)

    def print_queries(self):
        for q in self.queries:
            print(f"SQL:")
            print(f'    {q["sql"]}')
            print("CALLER:")
            print(f"    {q['caller']}")
            print()

    @staticmethod
    def get_traceback(limit=20, ignore_modules=None):
        if ignore_modules is None:
            ignore_modules = []
        tb = traceback.format_stack()[:-1]  # Axe last line as it's this function
        filtered_tb = []
        for line in tb:
            append = True
            for module_string in ignore_modules:
                if module_string in line:
                    append = False
                    break
            if append:
                filtered_tb.append(line)

        filtered_tb = filtered_tb[
                      -limit:
                      ]  # Filter on limit. Filter from start since recent lines are at the end.
        return "".join(filtered_tb)

    def print_stats(self):
        print(f"TOTAL Queries: {len(self.queries)}")
