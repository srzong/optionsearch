import sys
import os
import time
import logging
from datetime import datetime
import requests

ARGS = {}

IC_CS_DELTA_RANGE = (0.165, 0.28)
IC_CB_DELTA_RANGE = (0.01, 0.27)
IC_PS_DELTA_RANGE = (-0.29, -0.165)
IC_PB_DELTA_RANGE = (-0.28, -0.01)

CSR_CS_DELTA_RANGE = (0.165, 0.36)
CSR_CB_DELTA_RANGE = (0.01, 0.34)
PSR_PS_DELTA_RANGE = (-0.40, -0.165)
PSR_PB_DELTA_RANGE = (-0.38, -0.01)

MIN_ET = 0
MIN_TC = 0
MIN_TCW = 33.4
MIN_TCU = 0

SELL_SYMMETRY = 1 #0.12
TOTAL_SYMMETRY = 1 #0.25
WIDTH_SYMMETRY = 10 #10, no use

# SORT_KEYS = ("et", "ml", "width", "tc_w","tc", "symm", "tc_u", "tcc", "tcc_w")

NON_REVERSE_SORT = {"width", "ml", "symm"}
PRINT_PROPS = ["et", "etp", "etc", "tc", "tcp", "tcc", "tc_w", "tcp_w", "tcc_w", "tc_u", "tcp_u", "tcc_u", "beven", "bevenp", "bevenc"]
OPTION_PROPS = ["description", "symbol", "putCall", "strikePrice", "bid", "ask", "last", "mark", "bidAskSize",
    "highPrice", "lowPrice", "openPrice", "closePrice", "totalVolume", 
    "netChange", "volatility", "delta", "gamma", "theta", "vega", "openInterest", "timeValue",
    "theoreticalOptionValue", "daysToExpiration"]
loglevel = logging.INFO # DEBUG or INFO or ERROR

def get_dateString(day_delta=0, from_date=None):
   
    if from_date:
        fields = from_date.split('-')
        if len(fields) != 3 or len(fields[0]) != 4:
            print(f"unexpected date format: {from_date}")
            raise ValueError()
        year = int(fields[0])
        month = int(fields[1])
        day = int(fields[2])
        dt = datetime(year=year, month=month, day=day)
        ts = datetime.timestamp(dt)
    else:
        ts = time.time()
    

    if day_delta:
        seconds_in_day = 24.0 * 60.0 * 60.0
        ts += seconds_in_day * day_delta
    dt = datetime.fromtimestamp(ts)
    dt = datetime(year=dt.year, month=dt.month, day=dt.day)
    date_str = f"{dt.year}-{dt.month:02}-{dt.day:02}"
    return date_str

def getDayCount(datestr):
    date_fields = datestr.split('-')
    year = int(date_fields[0])
    month = int(date_fields[1])
    day = int(date_fields[2])
    dt = datetime(year=year, month=month, day=day)
    count = int((dt.timestamp() - time.time()) // (24*60*60))
    return count
  

"""
def check_delta_range(delta, option_type=None, c_delta=None):
    if ARGS["skip_delta"]:
        return True
    if option_type == "cs":
        lbnd = CS_DELTA_RANGE[0]
        ubnd = CS_DELTA_RANGE[1]
    elif option_type == "cb":
        lbnd = CB_DELTA_RANGE[0]
        ubnd = CB_DELTA_RANGE[1]
        if c_delta:
            if c_delta > ubnd:
                ubnd = c_delta 
    elif option_type == "ps":
        lbnd = PS_DELTA_RANGE[0]
        ubnd = PS_DELTA_RANGE[1]
        if c_delta:
            if ubnd < -c_delta: 
                ubnd = -c_delta
            logging.debug(f"ps: c_delta= {c_delta:.3f} lbnd= {lbnd:.3f} ubnd= {ubnd:.3f}")
        else:
            logging.debug(f"ps: c_delta=None lbnd= {lbnd:.3f} ubnd= {ubnd:.3f}")

    
    elif option_type == "pb":
        lbnd = PB_DELTA_RANGE[0]
        ubnd = PB_DELTA_RANGE[1]
        if c_delta:
            if c_delta > lbnd:
                lbnd = c_delta
    else:
        logging.error("invalid call type")
        sys.exit(1)
    
    logging.debug(f"check_delta_range: delta= {delta:.3f} lbnd= {lbnd:.3f} ubnd= {ubnd:.3f}")
    
    #if ubnd < lbnd:
    #    logging.warning("expected delta check upper bound to be greater than lower bound")
    #    return False
    
    if lbnd <= delta and delta <= ubnd:
        return True

    return False
"""
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_headers():
    with open("auth_token", "r") as f:
        data = f.read().strip()
    headers = {"Authorization": "Bearer " + data}
    return headers

def descIsCall(desc):
    if desc.find("Call") > 0:
        return True
    else:
        return False

def descIsPut(desc):
    if desc.find("Put") > 0:
        return True
    else:
        return False
 

class Option:     
        
    def __init__(self, propmap):
        self._propmap = propmap

    def __str__(self):
        s = f"{self.desc} -- delta: {self.delta:.2f} price: {self.price:.2f} strike: {self.strike}"
        return s

    @property
    def desc(self):
        return self._propmap["description"]

    @property
    def delta(self):
        return self._propmap["delta"]

    @property
    def price(self):
        return self._propmap["mark"]
 
    @property
    def strike(self):
        return self._propmap["strikePrice"]

    def isProp(self, propname):
        if propname in OPTION_PROPS and propname in self._propmap:
            return True
        else:
            return False
    def getProp(self, propname):
        return self._propmap[propname]

    def getPropNames(self):
        propnames = []
        for propname in OPTION_PROPS:
            if propname in self._propmap:
                propnames.append(propname)
        return propnames


class Candidate:
    def __init__(self, cs=None, cb=None, ps=None, pb=None, underlying=None, volatility=None, interestRate=None, expireDate=None):
        self._cs = cs
        self._cb = cb
        self._ps = ps
        self._pb = pb
        self._underlying = underlying
        self._volatility = volatility
        self._interestRate = interestRate
        self._expireDate = expireDate
        self._props = {}
        self._prop_ranks = {}   
        self._prop_orders = {}
        logging.info(f"Candidate(cs={cs}, cb={cb}, ps={ps}, pb={pb})")

        # expected props when cs, cb, ps, and pb are defined:
        # tc
        # et
        # width
        # tc_w
        # ml
        # tc_u
        # symm
        
        if cs and cb and not ps and not pb:
            tcc = cs.price - cb.price
            width = cb.strike - cs.strike
            if not width:
                return
            delta_cc = 1.0 - cs.delta
            delta_cch = tcc * (cs.delta - cb.delta)/width
            delta_clh = cs.delta - cb.delta - delta_cch
            bevenc = 100 * (delta_cc + delta_cch)
            cl = width - tcc
            ecc = tcc * delta_cc
            ecch = 0.5 * tcc * delta_cch
            eclh = -0.5 * cl * delta_clh
            ecl = -cl * cb.delta
            etc = ecc + ecch + eclh + ecl
            tcc_w = 100 * (tcc / width)
            tcc_u = 100 * (tcc / underlying)

            logging.info("******************")
            logging.info(f"Cand CALL Spread: {cs.strike}/{cb.strike}" )
            logging.info(f"strike: {cs.strike:8.1f}  {cb.strike:8.1f}" )
            logging.info(f"delta:  {cs.delta:8.3f}  {cb.delta:8.3f}" )
            logging.info(f"price:  {cs.price:8.3f}  {cb.price:8.3f}" )
            logging.info("******************")

            logging.info(f"tcc: {tcc:.3f}")
            logging.info(f"w: {width:.3f}")
            logging.info(f"delta_cc: {delta_cc:.3f}  delta_cch: {delta_cch:.3f}  delta_clh: {delta_clh:.3f}")
            logging.info(f"cl: {cl:.3f}")
            logging.info(f"ecc: {ecc:.3f}  ecch: {ecch:.3f}  eclh: {eclh:.3f}  ecl: {ecl:.3f}") 
            logging.info(f"etc: {etc:.3f}")
            logging.info(f"tcc/w: {tcc_w:.3f}")
            logging.info(f"tcc/u: {tcc_u:.3f}")
            logging.info(f"bevenc: {bevenc:.2f}")

            self._props["tcc"] = tcc
            self._props["width"] = width
            self._props["tcc_w"] = tcc_w
            self._props["tcc_u"] = tcc_u
            self._props["etc"] = etc
            self._props["bevenc"] = bevenc
            return
        elif ps and pb and not cs and not cb:
            tcp = ps.price - pb.price
            width = ps.strike - pb.strike
            if width:
                tcp_w = 100 * (tcp / width)
                tcp_u = 100 * (tcp / underlying)
                delta_pc = 1.0 + ps.delta   #+
                delta_pch = tcp * (pb.delta - ps.delta) / width #+
                delta_plh = pb.delta - ps.delta - delta_pch #+
                bevenp = 100 * (delta_pc + delta_pch)
                pl = width - tcp
                epc = tcp * delta_pc
                epch = 0.5 * tcp * delta_pch
                eplh = -0.5 * pl * delta_plh
                epl = pl * pb.delta
                etp = epc + epch + eplh + epl

                logging.info("******************")
                logging.info(f"Cand PUT Spread: {ps.strike}/{pb.strike}" )
                logging.info(f"strike: {ps.strike:8.1f}  {pb.strike:8.1f}" )
                logging.info(f"delta:  {ps.delta:8.3f}  {pb.delta:8.3f}" )
                logging.info(f"price:  {ps.price:8.3f}  {pb.price:8.3f}" )
                logging.info("******************")

                logging.info(f"tcp: {tcp:.3f}")
                logging.info(f"width: {width:.3f}")
                logging.info(f"delta_pc: {delta_pc:.3f}  delta_pch: {delta_pch:.3f}  delta_plh: {delta_plh:.3f}")
                logging.info(f"pl: {pl:.3f}")
                logging.info(f"epc: {epc:.3f}  epch: {epch:.3f}  eplh: {eplh:.3f}  epl: {epl:.3f}") 
                logging.info(f"etp: {etp:.3f}")
                logging.info(f"tcp/w: {tcp_w:.3f}")
                logging.info(f"tcp/u: {tcp_u:.3f}")
                logging.info(f"bevenp: {bevenp:.2f}")

                self._props["tcp"] = tcp
                self._props["width"] = width
                self._props["tcp_w"] = tcp_w
                self._props["tcp_u"] = tcp_u
                self._props["etp"] = etp
                self._props["bevenp"] = bevenp
            return
        elif not cs or not cb or not ps or not pb:
            logging.warning("unexpected candidate constructor")
            return
        
        # calculations based on cs, cb, ps, and pb being set
        css = cs.strike
        csp = cs.price
        csd = cs.delta
        cbs = cb.strike
        cbp = cb.price
        cbd = cb.delta
        pss = ps.strike
        psp = ps.price
        psd = ps.delta
         
        pbs = pb.strike
        pbp = pb.price
        pbd = pb.delta 
        
        logging.info("******************")
        logging.info(f"Cand IC: {css}/{cbs}/{pss}/{pbs}" )
        
        logging.info(f"strike: {css:8.1f}  {cbs:8.1f}  {pss:8.1f}  {pbs:8.1f}" )
        logging.info(f"delta:  {csd:8.3f}  {cbd:8.3f}  {psd:8.3f}  {pbd:8.3f}" )
        logging.info(f"price:  {csp:8.3f}  {cbp:8.3f}  {psp:8.3f}  {pbp:8.3f}" )
 
        logging.info("******************")
        
        tc = csp - cbp + psp - pbp
        #width = ((cbs - css) + (pss - pbs)) * 0.5
        width = cbs - css
        if cbs-css < psp-pbp:
            width = psp - pbp
        symm = csd + cbd + psd + pbd

        logging.info(f"tc: {tc:.3f}")
        logging.info(f"width: {width:.3f}")
        
        logging.info(f"symm: {symm:.3f}")
        logging.info(f"cbs - css: {(cbs - css):.3f}")
        logging.info(f"pss - pbs: {(pss - pbs):.3f}")
      
        try:
            etca = tc * (1.0 - csd + psd) 
            delta_cc = tc * (csd - cbd)/(cbs - css)
            delta_pc = tc * (psd - pbd)/(pss - pbs) #-
            delta_cd = csd - cbd - delta_cc
            delta_pd = psd - pbd - delta_pc #-
            tcl = cbs - css - tc
            tpl = pss - pbs - tc
            beven = 100 * (1.0 - csd + psd + delta_cc - delta_pc) 
            
            logging.info(f"d_cc: {delta_cc:.3f}")
            logging.info(f"d_pc:  {delta_pc:.3f}")   
            logging.info(f"d_cd: {delta_cd:.3f}")
            logging.info(f"d_pd: {delta_pd:.3f}")            
            logging.info(f"tcl:  {tcl:.3f}")            
            logging.info(f"tpl: {tpl:.3f}")
            logging.info(f"beven: {beven:.2f}")
            
            etcch = 0.5 * tc * delta_cc
            etpch = -0.5 * tc * delta_pc
            etcdh = -0.5 * tcl * delta_cd 
            etpdh = 0.5 * tpl * delta_pd 
            etcd = -tcl * cbd 
            etpd = tpl * pbd 
            et = etca + etcch + etcdh + etpch + etpdh + etcd + etpd
            
            
            """
            logging.info(f"etca: {etc:.3f}")
            logging.info(f"ecch: {etcch:.3f}")
            logging.info(f"epch: {etpch:.3f}")
            logging.info(f"ecdh: {etcdh:.3f}")
            logging.info(f"epdh: {etpdh:.3f}")
            logging.info(f"ecd: {etcd:.3f}")
            logging.info(f"epd: {etpd:.3f}")
            
            logging.info(f"et: {et:.3f}")
            logging.info(f"tc_u: {tc_u:.4f}")    
            """
            tc_w = 100 * (tc / width)
            tc_u = 100 * (tc / underlying)
  
            # set properties
            self._props["tc"] = tc
            self._props["width"] = width
            self._props["et"] = et
            self._props["tc_w"] = tc_w

            #self._props["symm"] = abs(symm)
            self._props["tc_u"] = tc_u
            self._props["beven"] = beven
        except ZeroDivisionError:
            logging.info("zerodivisionerror")
              
    def __str__(self):
        return f"{self._cs}/{self._cb}/{self._pb}/{self._ps}"

    def print_verbose(self, total=None, min_vals=None, max_vals=None):
        #print(candidate.keys())
        print() 
        if self._cs and self._cb and self._ps and self._pb:
            print(f"IC: {self._cs.strike}/{self._cb.strike}/{self._ps.strike}/{self._pb.strike}" )
        elif self._cs and self._cb:
            print(f"CSpd: {self._cs.strike}/{self._cb.strike}" )
        elif self._ps and self._pb:
            print(f"PSpd: {self._ps.strike}/{self._pb.strike}" )

        if self._cs:
            print("cs:", self._cs)
        if self._cb:
            print("cb:", self._cb)
        if self._ps:
            print("ps:", self._ps)
        if self._pb:
            print("pb:", self._pb)
        print("----")

        if PRINT_PROPS:
            propnames = PRINT_PROPS
        else:
            propnames = list(self.get_props())
            propnames.sort()

        for propname in propnames:
            if not propname in self._props:
                continue
            propval = self.get_prop(propname)
            proprank = self.get_rank(propname)

            s = f"{propname}: {propval:.3f}"
            """
            if propname == "tc_w" or propname == "tc_u"
                or propname == "tcc_w" or propname == "tcc_u"
                or propname == "tcp_w" or propname == "tcp_u":
                s += "%"
            """    
            if proprank:
                s += f" rank: {proprank}"
            if total:
                s += f"/{total}"
            if min_vals and max_vals:
                min_val = min_vals[propname]
                max_val = max_vals[propname]
                if max_val > min_val:
                    percent = int((propval - min_val) * 100.0 / (max_val - min_val))
                else:
                    percent = 0
                s += f" [{min_val:.3f}, {max_val:.3f}] {percent}%"
            if "sort_key" in ARGS and ARGS["sort_key"] == propname:
                s += " *"
            print(s)

        """    
        if self._cs and self._ps:
            ssymm = self._cs.delta + self._ps.delta
            print(f"sell symm: {ssymm:.3f} ")
        """

    @property
    def cs(self):
        return self._cs

    @property
    def cb(self):
        return self._cb

    @property
    def pb(self):
        return self._pb

    @property
    def ps(self):
        return self._ps

    @property
    def underlying(self):
        return self._underlying

    @property
    def volatility(self):
        return self._volatility

    @property
    def interestRate(self):
        return self._interestRate

    @property
    def expireDate(self):
        return self._expireDate

    def get_props(self):
        return self._props.keys()

    def get_prop(self, propname):
        if propname in self._props:
            return self._props[propname]
         
        logging.warning(f"get_prop unexpected propname: [{propname}]")

    def has_prop(self, propname):
        return propname in self._props
         
    def set_prop(self, propname, value):
        if propname in self._props:
            self._props[propname] = value
        logging.warning(f"set_prop unexpected propname: [{propname}]")
         

    def get_rank(self, propname):
        if propname not in self._props:
            logging.error(f"get_rank, unexpected propname: {propname}")
            return None
        if propname not in self._prop_ranks:
            logging.warning(f"rank not set for {propname}")
            return None
        return self._prop_ranks[propname]
 

    def set_rank(self, propname, value):
        if propname not in self._props:
            logging.error(f"set_rank, unexpected propname: {propname}")
            return 
        
        self._prop_ranks[propname] = value
         
    def get_order(self, propname):
        if propname not in self._props:
            logging.error(f"get_order, unexpected propname: {propname}")
            return None
        if propname not in self._prop_orders:
            logging.warning(f"order not set for {propname}")
            return None
        return self._prop_orders[propname]
    
    def set_order(self, propname, value):
        if propname not in self._props:
            logging.error(f"set_order, unexpected propname: {propname}")
            return
        
        self._prop_orders[propname] = value

    def meets_requirements(self):
        logging.info(f"requirements check")

        if self._cs and self._cb and self._ps and self._pb:
            # IC

            for propname in ("et", "tc", "tc_w", "tc_u"):
                if propname not in self._props:
                    logging.info(f"meet_requirements, {propname} not set")
                    return False

            et = self._props["et"]
            tc = self._props["tc"]
            tc_w = self._props["tc_w"]
            tc_u = self._props["tc_u"]

            if et < MIN_ET:
                logging.debug(f"BAD et: {et} < {MIN_ET}")
                return False

            if tc < MIN_TC:
                logging.debug(f"BAD tc: {tc} < {MIN_TC}")
                return False
                
            if tc_w < MIN_TCW:
                logging.info(f"BAD tcw check: {tc_w} < {MIN_TCW}")
                return False

            if tc_u < MIN_TCU:
                logging.info(f"BAD tcu: {tc_u} < {MIN_TCW}")
                return False

            """
            if self._ps.strike - self._pb.strike <= tc:
                logging.info(f"BAD tail: put < tc {tc}")
                return False   
        
            if self._cb.strike - self._cs.strike <= tc:
                logging.info(f"BAD tail: call < tc {tc}")
                return False  
            """
        elif self._cs and self._cb:
            # call spread
            for propname in ("etc", "tcc", "tcc_w", "tcc_u"):
                if propname not in self._props:
                    logging.info(f"meet_requirements, {propname} not set")
                    return False

            etc = self._props["etc"]
            tcc = self._props["tcc"]
            tcc_w = self._props["tcc_w"]
            tcc_u = self._props["tcc_u"]

            if etc < MIN_ET:
                logging.info(f"BAD etc: {etc} < {MIN_ET}")
                return False

            if tcc < MIN_TC:
                logging.info(f"BAD tcc: {tcc} < {MIN_TC}")
                return False
        
            if tcc_u < MIN_TCU:
                logging.info(f"BAD tcu: {tcc_u} < {MIN_TCW}")
                return False

            if tcc_w < MIN_TCW:
                logging.info(f"BAD tcw check: {tcc_w} < {MIN_TCW}")
                return False

        elif self._ps and self._pb:
            # put spread
            for propname in ("etp", "tcp", "tcp_w", "tcp_u"):
                if propname not in self._props:
                    logging.info(f"meet_requirements, {propname} not set")
                    return False

            etp = self._props["etp"]
            tcp = self._props["tcp"]
            tcp_w = self._props["tcp_w"]
            tcp_u = self._props["tcp_u"]
                    
            if etp < MIN_ET:
                logging.info(f"BAD etp: {etp} < {MIN_ET}")
                return False

            if tcp < MIN_TC:
                logging.info(f"BAD tcp: {tcp} < {MIN_TC}")
                return False

            if tcp_w < MIN_TCW:
                logging.info(f"BAD tcpw check: {tcp_w} < {MIN_TCW}")
                return False

            if tcp_u < MIN_TCU:
                logging.info(f"BAD tcpu: {tcp_u} < {MIN_TCW}")
                return False
    
        return True

        
def printCandidates(candidates):
    total = len(candidates)
    # propnames = ("et", "ml", "width", "tc_w", "tc", "symm", "tc_u", "tcc", "tcc_w")
    propnames = set()
    min_vals = {}
    max_vals = {}
    for candidate in candidates:
        if not propnames:
            for name in candidate.get_props():
                propnames.add(name)
        for propname in propnames:
            if not candidate.has_prop(propname):
                continue
            val = candidate.get_prop(propname)
            if propname in min_vals:
                if val < min_vals[propname]:
                    min_vals[propname] = val
            else:
                min_vals[propname] = val
            if propname in max_vals:
                if val > max_vals[propname]:
                    max_vals[propname] = val
            else:
                max_vals[propname] = val
    for candidate in candidates:
        candidate.print_verbose(total=total, min_vals=min_vals, max_vals=max_vals)
        print("------------")

def get_chains(symbol, dt_min, dt_max):
    
    headers = get_headers()
    params = {}
    params["symbol"] = symbol
    params["strikeCount"] = 200
    params["includeQuotes"] = True
    params["strategy"] = "ANALYTICAL"
    params["interval"] = 1
    params["fromDate"] = f"{dt_min.year}-{dt_min.month}-{dt_min.day}"
    params["toDate"] = f"{dt_max.year}-{dt_max.month}-{dt_max.day}"
    logging.info(f"fromDate: {dt_min.year}-{dt_min.month}-{dt_min.day}")
    logging.info(f"toDate: {dt_max.year}-{dt_max.month}-{dt_max.day}")
    params["daysToExpiration"] = 45
    req = "https://api.tdameritrade.com/v1/marketdata/chains"
    rsp = requests.get(req, params=params, headers=headers)
    if rsp.status_code != 200:
        logging.error(f"got bad status code: {rsp.status_code}")
        return None
    rsp_json = rsp.json()
    if rsp_json["status"] == "FAILED":
        logging.error("got FAILED status")
        return None
    #logging.info(rsp_json)
    return rsp_json

def get_options(option_map, underlying):
    results = []
    expire_date = None
    for expDate in option_map:
        if expire_date:
            if expDate != expire_date:
                continue
        else:
            expire_date = expDate
        bundle = option_map[expDate]
        for strikePrice in bundle:
            options = bundle[strikePrice]
            for option in options:
                description = option["description"]
                print("description:", description)
                strike = float(strikePrice)
                if descIsPut(description):
                    if underlying <= strike:
                        logging.info(f"skip put, underlying: {underlying} strike: {strike}")
                        continue
                elif descIsCall(description):
                    if underlying >= strike:
                        logging.info(f"skip call, underlying: {underlying} strike: {strike}")
                        continue
                else:
                    logging.info(f"unexpected description: {description}")
                    sys.exit(1)
                 
                #price = (option["bid"] + option["ask"])/2.0
                item = Option(option)

                results.append(item)
    
    # remove the :nn from expire date 
    # e.g.: 2020-03-20:47 -> 2020-03-20
    n = expire_date.find(":")
    if n > 0:
        expire_date = expire_date[:n]
    return (results, expire_date)
    
def get_contracts(symbol, chains):
    underlying = chains["underlyingPrice"]
    volatility = chains["volatility"]
    interestRate = chains["interestRate"]
    #daysToExpiration = chains["daysToExpiration"]
    putMap = chains["putExpDateMap"]
    callMap = chains["callExpDateMap"]
    
    (put_options, put_expire_date) = get_options(putMap, underlying)
    logging.info(f"got {len(put_options)} put options, expire_date: {put_expire_date}")
    (call_options, call_expire_date) = get_options(callMap, underlying)
    logging.info(f"got {len(call_options)} call options, expire_date: {call_expire_date}")
    if put_expire_date != call_expire_date:
        logging.error("expected put expire date to equal call expire date")
        sys.exit(1)
    # save options to file
    today_ds = get_dateString()
    stock_dir = f"data/{symbol}"
    if not os.path.isdir(stock_dir):
        os.mkdir(stock_dir)
    filename = f"{stock_dir}/{symbol}-{today_ds}.txt"
    #run_time = datetime.fromtimestamp(time.time())
    with open(filename, 'w') as f:
        print(f"{symbol}, runtime: {dt.year}/{dt.month:02}/{dt.day:02} {dt.hour:02}:{dt.minute:02}")
        print(f"{symbol}, underlying: {underlying:12.3f}", file=f)
        print(f"{symbol}, volatility: {volatility:12.3f}", file=f)
        print(f"{symbol}, interestRate: {interestRate:12.3f}", file=f)
        print(f"{symbol}, expireDate: {put_expire_date}", file=f)
        daysToExpiration = getDayCount(put_expire_date)
        print(f"{symbol}, daysToExpiration: {daysToExpiration}", file=f)

        header = "#           description,                 "
        for propname in OPTION_PROPS[1:]:
            if propname == "daysToExpiration":
                continue
            header += f"{propname:>12},"

        print(header, file=f)

        options = []
        for option in put_options:
            options.append(option)
        for option in call_options:
            options.append(option)
       
        for option in options:   
            textline = f"{option.desc:40},"
            for propname in OPTION_PROPS[1:]:
                if propname == "daysToExpiration":
                    continue
                propval = option.getProp(propname)
                print(f"got propname: {propname} propval: {propval}")
                if isinstance(propval, float):
                    textline += f"{propval:12.3f},"
                elif isinstance(propval, str):
                    textline += f"{propval[:12]:>12},"
                else:
                    textline += f"{propval:>12},"

            print(textline, file=f)
         
    retval = {}
    retval["underlying"] = underlying
    retval["volatility"] = volatility
    retval["interestRate"] = interestRate
    retval["expireDate"] = put_expire_date
    retval["call"] = call_options
    retval["put"] = put_options
    return retval   

def load_from_file(symbol, dt_min=None, dt_max=None, useold=False):
    # search data files for valid file to load
    logging.info(f"load_file_file({symbol}, {dt_min}, {dt_max})")
    stock_dir = f"data/{symbol}"
    if not os.path.isdir(stock_dir):
        return None
    filenames = os.listdir(stock_dir)
    datafile = None
    logging.info(f"search data files with symbol {symbol} from {dt_min} to {dt_max}")
    if not dt_min:
        dt_min = datetime.fromisoformat("1900-01-01")
    if not dt_max:
        dt_max = datetime.fromisoformat("2100-12-31")
    for filename in filenames:
        if not filename.endswith(".txt"):
            continue
        filename = filename[:-4]  # drop extension
        n = filename.find('-')
        file_symbol = filename[:n]
        datestring = filename[(n+1):]
        if file_symbol != symbol:
            continue
        logging.info(f"looking at file: {filename}")
        file_date = datetime.fromisoformat(datestring)
        if file_date >= dt_min and file_date <= dt_max:
            datafile = filename
            # keep going to get most recent data file
    if not datafile:
        if useold and len(filenames) > 0:
            # grab the most recent file
            datafile = filenames[-1]
        else:
            logging.info("no datafile found")
            return None

    underlying = None
    calls = []
    puts = []
    with open(stock_dir+"/"+datafile+".txt") as f:
        line = f.readline().strip()
        # first line should be like: MMM, underlying:      158.630
        n = line.find(":")
        underlying = float(line[(n+1):])
        line = f.readline().strip()
        # next line should be volatility
        n = line.find(":")
        volatility = float(line[(n+1):])
        line = f.readline().strip()
        # next line should be interestRate
        n = line.find(":")
        interestRate = float(line[(n+1):])
        line = f.readline().strip()
        # next line should be expireDate
        n = line.find(":")
        expireDate = line[(n+1):].strip()
        line = f.readline().strip()
        n = line.find(":")
        daysToExpiration = int(line[(n+1):])
        logging.debug(f"got daysToExpiration: {daysToExpiration}")
        propnames = []
        # next line should be headers
        line = f.readline().strip()
        if line[0] != '#':
            logging.error(f"expected header line but got: {line}")
            sys.exit(1)
        line = line[1:]
        fields = line.split(',')
        for field in fields:
            propnames.append(field.strip())
        

        while line:
            line = f.readline().strip()
            if not line: 
                continue

            fields = line.split(',')
            if len(fields) != len(propnames):
                logging.error(f"unexpected line: {line}")
                continue
            optionprops = {}
            for i in range(len(fields)):
                propname = propnames[i]
                field = fields[i].strip()
                if len(field) == 0:
                    propval = ""
                else:
                    field_type = "int"
                    for ch in field:
                        if ch == '.' and field_type == "int":
                            field_type = "float"
                        elif ch == '-':
                            pass # ignore, could be neg sign
                        elif not ch.isdigit():
                            field_type = "str"
                    if field_type == "int":
                        propval = int(field)
                    elif field_type == "float":
                        propval = float(field)
                    else:
                        propval = field  # just string
                optionprops[propname] = propval
                
            option = Option(optionprops)
            if descIsPut(option.desc):
                puts.append(option)
            elif descIsCall(option.desc):
                calls.append(option)
            else:
                logging.error(f"unexpected desc: [{option.desc}]")

    logging.info(f"loaded {len(calls)} calls and {len(puts)} puts from file")
    retval = {}
    retval["underlying"] = underlying
    retval["interestRate"] = interestRate
    retval["volatility"] = volatility
    retval["expireDate"] = expireDate
    retval["call"] = calls
    retval["put"] = puts
    return retval
        

def prelimination(cs=None, cb=None, ps=None, pb=None):  
                     
    fmt = f"prelimination Checking:"
    if cs:
        fmt += f" {cs.strike:.1f}"
    if cb:
        fmt += f"/{cb.strike:.1f}"
    if ps:
        fmt += f"/{ps.strike:.1f}"
    if pb:
        fmt += f"/{pb.strike:.1f}"
    logging.debug(fmt)

    if cs and cs.strike >= cb.strike:
        logging.info("BAD prelimination call strike: sell > buy")
        return False

    if pb and pb.strike >= ps.strike:
        logging.info("BAD prelimination put strike: buy > sell")
        return False
    
    if ps and cs and ps.strike >= cs.strike:
        logging.info("BAD prelimination call/put strikes: put > call")
        return False

    if cs and cb and cs.price <= cb.price:
        logging.info("BAD prelimination call price: sell < buy")
        return False

    if ps and pb and ps.price <= pb.price:
        logging.info('BAD prelimination put price: sell < buy')
        return False

    return True

def check_ic_requirements(ic):
    if not ic.cs or not ic.cb or not ic.ps or not ic.pb:
        logging.error(f"invalid ic: {ic}")
        return False
    return check_ic_symmetry(ic)

def check_ic_symmetry(ic):
    logging.info(f"IC symmetry check: {ic.cs.strike:.1f}/{ic.cb.strike:.1f}/{ic.ps.strike:.1f}/{ic.pb.strike:.1f}" )
    
    if ic.cb.strike - ic.cs.strike > WIDTH_SYMMETRY * (ic.ps.strike - ic.pb.strike):
        logging.info(f"BAD width ratio call:put {ic.cb.strike - ic.cs.strike} : {ic.ps.strike - ic.pb.strike}")
        return False

    if ic.ps.strike - ic.pb.strike > WIDTH_SYMMETRY * (ic.cb.strike - ic.cs.strike):
        logging.info(f"BAD width ratio: put:call {ic.ps.strike - ic.pb.strike} : {ic.cb.strike - ic.cs.strike}")
        return False

    ssymm = ic.cs.delta + ic.ps.delta
    logging.info(f"sell symm = {ssymm:.3f}")
    if not abs(ssymm) < SELL_SYMMETRY:
        logging.info(f"BAD symmetry: sell delta: {abs(ssymm)} < {SELL_SYMMETRY}")
        return False

    symm = ic.cs.delta + ic.cb.delta + ic.ps.delta + ic.pb.delta
    if not abs(symm) < TOTAL_SYMMETRY:
        logging.info(f"BAD symmetry: over all symm = {ssymm:.3f} < {TOTAL_SYMMETRY}")
        return False

    return True      

def check_preq(candidate):
    if candidate.has_prop("et"):
        et = candidate.get_prop("et")
        tc = candidate.get_prop("tc")
        logging.debug(f"check_preq, got et: {et}, tc: {tc}")
    elif candidate.has_prop("etc"):
        et = candidate.get_prop("etc")
        tc = candidate.get_prop("tcc")
        logging.debug(f"check_preq, got etc: {et}, tcc: {tc}")      
    elif candidate.has_prop("etp"):
        et = candidate.get_prop("etp")
        #logging.debug(f"propnames: {candidate.get_props()}")
        tc = candidate.get_prop("tcp")
        logging.debug(f"check_preq, got etp: {et}, tcp: {tc}")
    else:
        logging.warning("expected to find either etc or etp property")
        return False
        
    if tc < MIN_TC:
        logging.debug("check_preq False -> tc < MIN_TC")
        return False
    if et < MIN_ET:
        logging.debug("check_preq False -> et < MIN_ET")
        return False

    logging.debug("check_preq True")
    return True


def get_candidates_put(contracts, ps_range=None, pb_range=None):
    # set default sort key
    if "sort_key" not in ARGS:
        ARGS["sort_key"] = "etp"
    candidates = []
    put_list = contracts["put"]
    if ps_range is None:
        ps_range = PSR_PS_DELTA_RANGE
    if pb_range is None:
        pb_range = PSR_PB_DELTA_RANGE

    pb_list = []
    for pb in put_list:
        logging.info(f"--------pb: strike:{pb.strike}, delta:{pb.delta}, price:{pb.price}")
       
        if pb.delta < pb_range[0] or pb.delta > pb_range[1]:
            logging.info(f"BAD delta range: put buy delta: {pb.delta}")
        else:
            pb_list.append(pb)

    logging.info(f"pb_list count: {len(pb_list)}")
    ps_list = []
    for ps in put_list:
        logging.info(f"------ps: strike:{ps.strike}, delta:{ps.delta}, price:{ps.price}")
            
        if ps.delta < ps_range[0] or ps.delta > ps_range[1]:
            logging.info(f"BAD delta range: put sell delta: {ps.delta}")
        else:
            ps_list.append(ps)
    logging.info(f"ps_list count: {len(ps_list)}")

    #for option in put_list:
        #print(f"put_list.strike: {option.strike:.3f}")
     
    underlying = contracts["underlying"]
    volatility = contracts["volatility"]
    interestRate = contracts["interestRate"]
    expireDate = contracts["expireDate"]
    total_count = 0
    meet_requirements_count = 0
    
    for pb in pb_list:
        logging.info(f"--------pb: strike:{pb.strike}, delta:{pb.delta}, price:{pb.price}")
        for ps in ps_list:
            if pb.strike >= ps.strike:
                logging.debug(f"skip pb.strike > ps.strike  {pb.strike}>{ps.strike}")
                continue
            logging.debug(f"------ps: strike:{ps.strike}, delta:{ps.delta}, price:{ps.price}")            
            
            if prelimination(ps=ps, pb=pb):
                total_count += 1
                candidate = Candidate(ps=ps, pb=pb, underlying=underlying, volatility=volatility, interestRate=interestRate, expireDate=expireDate)
                       
                if candidate.meets_requirements():
                    candidates.append(candidate)
                    meet_requirements_count += 1        

    print ("----------------------")
    print("total put candidates:", total_count)
    print("meet req candidates:", meet_requirements_count)                    
    return candidates


def get_candidates_call(contracts, cs_range=None, cb_range=None):
    # set default sort key
    if "sort_key" not in ARGS:
        ARGS["sort_key"] = "etc"
    candidates = []
    call_list = contracts["call"]
    if cs_range is None:
        cs_range = CSR_CS_DELTA_RANGE
    if cb_range is None:
        cb_range = CSR_CB_DELTA_RANGE

    cs_list = []
    for cs in call_list:
        logging.info(f"check--------cs: strike:{cs.strike}, delta:{cs.delta}, price:{cs.price}")
       
        if  cs.delta < cs_range[0] or cs.delta > cs_range[1]:
            logging.info(f"BAD delta range: call sell delta: {cs.delta}")
        else:
            cs_list.append(cs)
    logging.info(f"cs_list count: {len(cs_list)}")

    cb_list = []
    for cb in call_list:
        logging.info(f"check------cb: strike:{cb.strike}, delta:{cb.delta}, price:{cb.price}")
            
        if cb.delta < cb_range[0] or cb.delta > cb_range[1]:
            logging.info(f"BAD delta range: call but delta: {cb.delta}")
        else:
            cb_list.append(cb)
    logging.info(f"cb_list count: {len(cb_list)}")

     
    underlying = contracts["underlying"]
    volatility = contracts["volatility"]
    interestRate = contracts["interestRate"]
    expireDate = contracts["expireDate"]
    total_count = 0
    meet_requirements_count = 0
    
    for cs in cs_list:
        logging.info(f"--------cs: strike:{cs.strike}, delta:{cs.delta}, price:{cs.price}")
    
        for cb in cb_list:
            if cb.strike <= cs.strike:
                logging.info(f"skip cb.strike <= cs.strike: {cb.strike} <= {cs.strike}")
                continue
            logging.info(f"------cb: {cb.desc} strike:{cb.strike}, delta:{cb.delta}, price:{cb.price}")
               
            if prelimination(cs=cs, cb=cb):
                total_count += 1
                candidate = Candidate(cs=cs, cb=cb, underlying=underlying, volatility=volatility, interestRate=interestRate, expireDate=expireDate)
                       
                if candidate.meets_requirements():
                    candidates.append(candidate)
                    meet_requirements_count += 1

    print ("----------------------")
    print("total call candidates:", total_count)
    print("meet req candidates:", meet_requirements_count)    

    return candidates

def get_ic_candidates(contracts):
    if "sort_key" not in ARGS:
        ARGS["sort_key"] = "et"

    ic_candidates = []
    underlying = contracts["underlying"]
    volatility = contracts["volatility"]
    interestRate = contracts["interestRate"]
    expireDate = contracts["expireDate"]

    put_list = get_candidates_put(contracts, ps_range=IC_PS_DELTA_RANGE, pb_range=IC_PB_DELTA_RANGE)
    call_list = get_candidates_call(contracts, cs_range=IC_CS_DELTA_RANGE, cb_range=IC_CB_DELTA_RANGE)
 
       
    logging.info(f"get_ic_candidates put_list (count: {len(put_list)}):")
    for put in put_list:
        logging.info(put)
    logging.info(f"get_ic_candidates call_list (count: {len(call_list)}):")
    for call in call_list:
        logging.info(call)

    total_count = 0
    meet_requirements_count = 0
    
    for call in call_list:
        logging.info(f"--------ic calls: {call}")
    
        for put in put_list:
            logging.info(f"----------ic puts {put}")
            total_count += 1
            candidate = Candidate(cs=call.cs, cb=call.cb, ps=put.ps, pb=put.pb, underlying=underlying, volatility=volatility, interestRate=interestRate, expireDate=expireDate)
                       
            if candidate.meets_requirements(): # and check_preq(candidate):
                ic_candidates.append(candidate)
                meet_requirements_count += 1   

            
    print ("----------------------")
    print("total ic candidates:", total_count)
    print("meet req ic candidates:", meet_requirements_count)                    

    return ic_candidates

 
def print_usage():
    print("usage: python get_options.py [--skip-delta] [--sort prop] [--calls|--puts] [--reload|--useold|--dataonly] SYM")


#
# Main
#
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print_usage()
    sys.exit(1)

symbols = []
reload = False
useold = False
dataonly = False
ARGS["skip_delta"] = False
ARGS["option_type"] = "ALL"  # or CALLS_ONLY or PUTS_ONLY

# setup logging
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(loglevel)
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
#logging.basicConfig(format='LOG %(message)s', level=loglevel)
root.addHandler(handler)

dt_now = datetime.fromtimestamp(time.time())
print(f"run date: {dt_now.year}-{dt_now.month:02}-{dt_now.day:02}")

sort_key_arg = False
for argn in range(1, len(sys.argv)):
    argval = sys.argv[argn]
    if sort_key_arg:
        ARGS["sort_key"] = argval
        sort_key_arg = False
    elif argval.startswith('-'):
        if argval == "--skip-delta":
            ARGS["skip_delta"] = True
        elif argval == "--reload":
            reload = True
        elif argval == "--useold":
            useold = True    
        elif argval == "--dataonly":
            dataonly = True
        elif argval == "--calls":
            ARGS["option_type"] = "CALLS_ONLY"
        elif argval == "--puts":
            ARGS["option_type"] = "PUTS_ONLY"
        elif argval == "--sort":
            sort_key_arg = True       
        else:
            print_usage()
            sys.exit(1)
    else:
        symbols.append(argval)
if not symbols:
    print_usage()
    sys.exit(1)
if dataonly:
    reload = True
if reload and useold:
    print_usage()
    sys.exit(1)
symbol = symbols[0]
print("getting symbol:", symbol)

seconds_in_day = 24.0 * 60.0 * 60.0
exp_target_min = time.time() + 41.0 * seconds_in_day
exp_target_max = time.time() + 60.0 * seconds_in_day

dt = datetime.fromtimestamp(exp_target_min)
# get time as of midnight
dt_min = datetime(year=dt.year, month=dt.month, day=dt.day)
dt = datetime.fromtimestamp(exp_target_max)
dt_max = datetime(year=dt.year, month=dt.month, day=dt.day)
    
contracts = None
if not reload:
    # see if we can load from previous file
    contracts = load_from_file(symbol)

if not contracts:
    chains = get_chains(symbol, dt_min, dt_max)
    if not chains:
        print("could not get any options")
        sys.exit(1)
    contracts = get_contracts(symbol, chains)

    if dataonly:
        print("done!")
        sys.exit(0)


# contracts: {"underlying": underlying, "call": calls, "put": puts}

if ARGS["option_type"] == "CALLS_ONLY":
    option_types = ("call",)
elif ARGS["option_type"] == "PUTS_ONLY":
    option_types = ("put",)
else:
    option_types = ("call", "put")

for k in option_types:
    options = contracts[k]
    print(k, len(options))
    for option in options:
        print(option.desc, option.delta)

for k in option_types:
    options = contracts[k]
    if len(options) == 0:
        print("no candidates!")
        sys.exit(0)

if "call" not in option_types:
    candidates = get_candidates_put(contracts)
    print("got", len(candidates), "put candidates")
elif "put" not in option_types:
    candidates = get_candidates_call(contracts)
    print("got", len(candidates), "call candidates")
else:
    candidates = get_ic_candidates(contracts)
    print("got", len(candidates), "IC candidates")
 

print("======================")

propnames = set()
for candidate in candidates:
    for propname in candidate.get_props():
        propnames.add(propname)

logging.info(f"properties: {propnames}")

for propname in propnames:
    can_sort = True
    for candidate in candidates:
        if not candidate.has_prop(propname):
            can_sort = False
            break
    if not can_sort:
        continue
    if propname in NON_REVERSE_SORT:
        reverse = False
    else:
        reverse = True
    candidates.sort(key = lambda candidate: candidate.get_prop(propname), reverse=reverse)
    rank = 1
    order = 1
    prev = None
    for candidate in candidates:
        candidate.set_order(propname, order)
        val = candidate.get_prop(propname)
        if prev:
            if abs(val - prev) > 0.001:
                rank = order
        candidate.set_rank(propname, rank)
        order += 1
        prev = val


if len(candidates) == 0:
    print("no candidates!")
else:
    print("======================")
    sort_key = ARGS["sort_key"]
    first_candidate = candidates[0]
    #print("first_candidate:", first_candidate)
    #print("underlying:", first_candidate.underlying)
    #print("volatility:", first_candidate.volatility)
    underlying = first_candidate.underlying
    volatility = first_candidate.volatility
    interestRate = first_candidate.interestRate
    expireDate = first_candidate.expireDate
  
    daysToExpiration = getDayCount(expireDate) 
    print(f"{symbol}: underlying: {underlying} sorting by: [{sort_key}]")
    #print(f"{symbol}: volatility: {volatility}")
    #print(f"{symbol}: interestRate: {interestRate}")
    #print(f"{symbol}: expireDate: {expireDate}")
    print(f"{symbol}: daysToExpiration: {daysToExpiration}")
candidates.sort(key = lambda candidate: candidate.get_order(sort_key))

printCandidates(candidates)
 