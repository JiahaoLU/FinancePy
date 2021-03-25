##############################################################################
# Copyright (C) 2018, 2019, 2020 Dominic O'Kane
##############################################################################


import numpy as np
from math import log, exp, sqrt

from ...utils.error import FinError
from ...utils.date import Date
from ...utils.math import ONE_MILLION
from ...utils.global_vars import gDaysInYear
from ...models.black_scholes import BlackScholes
from ...utils.global_types import FinOptionTypes
from .equity_vanilla_option import EquityVanillaOption
from ...utils.helpers import label_to_string, check_argument_types

###############################################################################


class EquityVarianceSwap:
    """ Class for managing an equity variance swap contract. """

    def __init__(self,
                 start_date: Date,
                 maturity_date_or_tenor: (Date, str),
                 strikeVariance: float,
                 notional: float = ONE_MILLION,
                 payStrikeFlag: bool = True):
        """ Create variance swap contract. """

        check_argument_types(self.__init__, locals())

        if type(maturity_date_or_tenor) == Date:
            maturity_date = maturity_date_or_tenor
        else:
            maturity_date = start_date.addTenor(maturity_date_or_tenor)

        if start_date >= maturity_date:
            raise FinError("Start date after or same as maturity date")

        self._start_date = start_date
        self._maturity_date = maturity_date
        self._strikeVariance = strikeVariance
        self._notional = notional
        self._payStrikeFlag = payStrikeFlag

        # Replication portfolio is stored
        self._numPutOptions = 0
        self._numCallOptions = 0
        self._putWts = []
        self._put_strikes = []
        self._callWts = []
        self._call_strikes = []

###############################################################################

    def value(self,
              valuation_date,
              realisedVar,
              fairStrikeVar,
              libor_curve):
        """ Calculate the value of the variance swap based on the realised
        volatility to the valuation date, the forward looking implied
        volatility to the maturity date using the libor discount curve. """

        t1 = (valuation_date - self._start_date) / gDaysInYear
        t2 = (self._maturity_date - self._start_date) / gDaysInYear

        expectedVariance = t1 * realisedVar/t2
        expectedVariance += (t2-t1) * fairStrikeVar / t2

        payoff = expectedVariance - self._strikeVariance

        df = libor_curve.df(self._maturity_date)
        v = payoff * self._notional * df
        return v

###############################################################################

    def fairStrikeApprox(self,
                         valuation_date,
                         fwdStockPrice,
                         strikes,
                         volatilities):
        """ This is an approximation of the fair strike variance by Demeterfi
        et al. (1999) which assumes that sigma(K) = sigma(F) - b(K-F)/F where
        F is the forward stock price and sigma(F) is the ATM forward vol. """

        f = fwdStockPrice

        # TODO Linear interpolation - to be revisited
        atmVol = np.interp(f, strikes, volatilities)
        tmat = (self._maturity_date - valuation_date)/gDaysInYear

        """ Calculate the slope of the volatility curve by taking the end
        points in the volatilities and strikes to calculate the gradient."""

        dvol = volatilities[-1] - volatilities[0]
        dK = strikes[-1] - strikes[0]
        b = f * dvol / dK
        var = (atmVol**2) * sqrt(1.0 + 3.0*tmat*(b**2))
        return var

###############################################################################

    def fairStrike(self,
                   valuation_date,
                   stock_price,
                   dividend_curve,
                   volatilityCurve,
                   numCallOptions,
                   numPutOptions,
                   strikeSpacing,
                   discount_curve,
                   useForward=True):
        """ Calculate the implied variance according to the volatility surface
        using a static replication methodology with a specially weighted
        portfolio of put and call options across a range of strikes using the
        approximate method set out by Demeterfi et al. 1999. """

        self._numPutOptions = numPutOptions
        self._numCallOptions = numCallOptions

        call_type = FinOptionTypes.EUROPEAN_CALL
        put_type = FinOptionTypes.EUROPEAN_PUT

        tmat = (self._maturity_date - valuation_date)/gDaysInYear

        df = discount_curve._df(tmat)
        r = - log(df)/tmat

        dq = dividend_curve._df(tmat)
        q = - log(dq)/tmat

        s0 = stock_price
        g = exp(r*tmat)
        fwd = stock_price * g

        # This fixes the centre strike of the replication options
        if useForward is True:
            sstar = fwd
        else:
            sstar = stock_price

        """ Replication argument from Demeterfi, Derman, Kamal and Zhou from
        Goldman Sachs Research notes March 1999. See Appendix A. This aim is
        to use calls and puts to approximate the payoff of a log contract """

        minStrike = sstar - (numPutOptions+1) * strikeSpacing

        self._putWts = []
        self._put_strikes = []
        self._callWts = []
        self._call_strikes = []

        # if the lower strike is < 0 we go to as low as the strike spacing
        if minStrike < strikeSpacing:
            k = sstar
            klist = [sstar]
            while k >= strikeSpacing:
                k -= strikeSpacing
                klist.append(k)
            putK = np.array(klist)
            self._numPutOptions = len(putK) - 1
        else:
            putK = np.linspace(sstar, minStrike, numPutOptions+2)

        self._put_strikes = putK

        maxStrike = sstar + (numCallOptions+1) * strikeSpacing
        callK = np.linspace(sstar, maxStrike, numCallOptions+2)

        self._call_strikes = callK

        optionTotal = 2.0*(r*tmat - (s0*g/sstar-1.0) - log(sstar/s0))/tmat

        self._callWts = np.zeros(numCallOptions)
        self._putWts = np.zeros(numPutOptions)

        def f(x): return (2.0/tmat)*((x-sstar)/sstar-log(x/sstar))

        sumWts = 0.0
        for n in range(0, self._numPutOptions):
            kp = putK[n+1]
            k = putK[n]
            self._putWts[n] = (f(kp)-f(k))/(k-kp) - sumWts
            sumWts += self._putWts[n]

        sumWts = 0.0
        for n in range(0, self._numCallOptions):
            kp = callK[n+1]
            k = callK[n]
            self._callWts[n] = (f(kp)-f(k))/(kp-k) - sumWts
            sumWts += self._callWts[n]

        piPut = 0.0
        for n in range(0, numPutOptions):
            k = putK[n]
            vol = volatilityCurve.volatility(k)
            opt = EquityVanillaOption(self._maturity_date, k, put_type)
            model = BlackScholes(vol)
            v = opt.value(valuation_date, s0, discount_curve,
                          dividend_curve, model)
            piPut += v * self._putWts[n]

        piCall = 0.0
        for n in range(0, numCallOptions):
            k = callK[n]
            vol = volatilityCurve.volatility(k)
            opt = EquityVanillaOption(self._maturity_date, k, call_type)
            model = BlackScholes(vol)
            v = opt.value(valuation_date, s0, discount_curve,
                          dividend_curve, model)
            piCall += v * self._callWts[n]

        pi = piCall + piPut
        optionTotal += g * pi
        var = optionTotal

        return var

###############################################################################

    def realisedVariance(self, closePrices, useLogs=True):
        """ Calculate the realised variance according to market standard
        calculations which can either use log or percentage returns."""

        num_observations = len(closePrices)

        for i in range(0, num_observations):
            if closePrices[i] <= 0.0:
                raise FinError("Stock prices must be greater than zero")

        cumX2 = 0.0

        if useLogs is True:
            for i in range(1, num_observations):
                x = log(closePrices[i]/closePrices[i-1])
                cumX2 += x*x
        else:
            for i in range(1, num_observations):
                x = (closePrices[i]-closePrices[i-1])/closePrices[i-1]
                cumX2 += x*x

        var = cumX2 * 252.0 / num_observations
        return var


###############################################################################

    def printWeights(self):
        """ Print the list of puts and calls used to replicate the static
        replication component of the variance swap hedge. """

        if self._numPutOptions == 0 and self._numCallOptions == 0:
            print("No call or put options generated.")
            return

        print("TYPE", "STRIKE", "WEIGHT")
        for n in range(self._numPutOptions-1, -1, -1):
            k = self._put_strikes[n]
            wt = self._putWts[n]*self._notional
            print("PUT %7.2f %10.3f" % (k, wt))

        for n in range(0, self._numCallOptions):
            k = self._call_strikes[n]
            wt = self._callWts[n]*self._notional
            print("CALL %7.2f %10.3f" % (k, wt))

###############################################################################

    def __repr__(self):
        s = label_to_string("OBJECT TYPE", type(self).__name__)
        s += label_to_string("START DATE", self._start_date)
        s += label_to_string("MATURITY DATE", self._maturity_date)
        s += label_to_string("STRIKE VARIANCE", self._strikeVariance)
        s += label_to_string("NOTIONAL", self._notional)
        s += label_to_string("PAY STRIKE FLAG", self._payStrikeFlag, "")
        return s

###############################################################################

    def _print(self):
        """ Simple print function for backward compatibility. """
        print(self)

###############################################################################
