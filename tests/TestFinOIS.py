###############################################################################
# Copyright (C) 2018, 2019, 2020 Dominic O'Kane
###############################################################################

import sys
sys.path.append("..")

from financepy.utils.math import ONE_MILLION
from financepy.products.rates.FinOIS import FinOIS
from financepy.market.discount.curve_flat import DiscountCurveFlat
from financepy.utils.frequency import FrequencyTypes
from financepy.utils.day_count import DayCountTypes
from financepy.utils.date import Date
from financepy.utils.global_types import FinSwapTypes

from FinTestCases import FinTestCases, globalTestCaseMode
testCases = FinTestCases(__file__, globalTestCaseMode)

###############################################################################

def test_FinFixedOIS():

    # Here I follow the example in
    # https://blog.deriscope.com/index.php/en/excel-quantlib-overnight-index-swap

    effectiveDate = FinDate(30, 11, 2018)
    endDate = FinDate(30, 11, 2023)

    endDate = effectiveDate.addMonths(60)
    oisRate = 0.04
    fixedLegType = FinSwapTypes.PAY
    fixedFreqType = FinFrequencyTypes.ANNUAL
    fixedDayCount = FinDayCountTypes.ACT_360
    floatFreqType = FinFrequencyTypes.ANNUAL
    floatDayCount = FinDayCountTypes.ACT_360
    floatSpread = 0.0
    notional = ONE_MILLION
    paymentLag = 1
    
    ois = FinOIS(effectiveDate,
                 endDate,
                 fixedLegType,
                 oisRate,
                 fixedFreqType,
                 fixedDayCount,
                 notional,
                 paymentLag,
                 floatSpread,
                 floatFreqType,
                 floatDayCount)

#    print(ois)

    valueDate = effectiveDate
    marketRate = 0.05
    oisCurve = FinDiscountCurveFlat(valueDate, marketRate,
                                    FinFrequencyTypes.ANNUAL)

    v = ois.value(effectiveDate, oisCurve)
    
#    print(v)
    
#    ois._fixedLeg.printValuation()
#    ois._floatLeg.printValuation()
    
    testCases.header("LABEL", "VALUE")
    testCases.print("SWAP_VALUE", v)
    
###############################################################################

test_FinFixedOIS()
testCases.compareTestCases()
