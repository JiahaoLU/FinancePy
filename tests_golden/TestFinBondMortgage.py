###############################################################################
# Copyright (C) 2018, 2019, 2020 Dominic O'Kane
###############################################################################

import sys
sys.path.append("..")

from financepy.utils.date import Date

from financepy.products.bonds.bond_mortgage import BondMortgage
from financepy.products.bonds.bond_mortgage import BondMortgageTypes
from financepy.products.rates.ibor_single_curve import IborSingleCurve

from FinTestCases import FinTestCases, globalTestCaseMode
testCases = FinTestCases(__file__, globalTestCaseMode)


###############################################################################


def test_BondMortgage():

    principal = 130000
    start_date = Date(23, 2, 2018)
    end_date = start_date.addTenor("10Y")
    mortgage = BondMortgage(start_date, end_date, principal)

    rate = 0.035
    mortgage.generate_flows(rate, BondMortgageTypes.REPAYMENT)

    num_flows = len(mortgage._schedule._adjusted_dates)

    testCases.header("PAYMENT DATE", "INTEREST", "PRINCIPAL", "OUTSTANDING",
                     "TOTAL")

    for i in range(0, num_flows):
        testCases.print(mortgage._schedule._adjusted_dates[i],
                        mortgage._interest_flows[i],
                        mortgage._principalFlows[i],
                        mortgage._principalRemaining[i],
                        mortgage._totalFlows[i])

    mortgage.generate_flows(rate, BondMortgageTypes.INTEREST_ONLY)

    testCases.header("PAYMENT DATE", "INTEREST", "PRINCIPAL", "OUTSTANDING",
                     "TOTAL")

    for i in range(0, num_flows):
        testCases.print(mortgage._schedule._adjusted_dates[i],
                        mortgage._interest_flows[i],
                        mortgage._principalFlows[i],
                        mortgage._principalRemaining[i],
                        mortgage._totalFlows[i])


###############################################################################


test_BondMortgage()
testCases.compareTestCases()
