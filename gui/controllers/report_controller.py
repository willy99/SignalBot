from dics.deserter_xls_dic import *
from gui.model.person import Person

class ReportController:
    def __init__(self, worklow):
        self.reporter = worklow.reporter

    def do_subunit_desertion_report(self, year):
        results = self.reporter.get_subunit_desertion_stats(year)
        return results
