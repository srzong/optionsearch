import sys
import time
from datetime import datetime
import requests


CSS_RANGE = (0.165,0.4)
CBS_RANGE = (0.05,0.16)
PSS_RANGE = (-0.4,-0.165)
PBS_RANGE = (-0.16,-0.05)


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

def to_string_candidate(candidate):
    desc = candidate["description"]
    delta = candidate["delta"]
    strike = candidate["strike"]
    price = candidate["price"]

    s = f"{desc} -- delta: {delta:.2f} strike: {strike:.2f} price: {price:.2f} "
    return s

def printCandidates(candidates):
    for candidate in candidates:
        #print(candidate.keys())
        width = candidate["width"]
        ml = candidate["ml"]
        tc = candidate["Tc"]
        tc_rank = candidate["Tc_rank"]
        et = candidate["Et"]
        et_rank = candidate["Et_rank"]

        tc_width = candidate["Tc_width"]
        tc_width_rank = candidate["Tc_width_rank"]
        et_width = candidate["Et_width"]
        et_width_rank = candidate["Et_width_rank"]
        Et_ml = candidate["Et_ml"]
        Et_ml_rank = candidate["Et_ml_rank"]
        tc_ml = candidate["Tc_ml"]
        tc_ml_rank = candidate["Tc_ml_rank"]
        Et_tc = candidate["Et_tc"]
        Et_tc_rank = candidate["Et_tc_rank"]

        #petc = candidate["petc"]
        print("cs:", to_string_candidate(candidate["cs"]))
        print("cb:", to_string_candidate(candidate["cb"]))
        print("ps:", to_string_candidate(candidate["ps"]))
        print("pb:", to_string_candidate(candidate["pb"]))
        #print("----")
        
        print(f"et: {et:.3f} rank: {et_rank}")
        print(f"tc: {tc:.2f} rank: {tc_rank}")
        print(f"width: {width:.2f}")
        print(f"ml: {ml:.2f}")
        print(f"tc/width: {100*tc_width:.2f}% rank: {tc_width_rank}")
        #print(f"tc/ml: {tc_ml:.2f} rank: {tc_ml_rank}")
        print(f"et/width: {100*et_width:.2f}% rank: {et_width_rank}")
        #print(f"et/ml: {Et_ml:.2f} rank: {Et_ml_rank}")
        print(f"et/tc: {100*Et_tc:.2f}% rank: {Et_tc_rank}")

        
       # print(f"et/tc: {Et_tc:.2f} rank: {Et_tc_rank}")
        print("------------")

def get_chains(symbol):
    seconds_in_day = 24.0 * 60.0 * 60.0
    exp_target_min = time.time() + 41.0 * seconds_in_day
    dt_min = datetime.fromtimestamp(exp_target_min)
    exp_target_max = time.time() + 60.0 * seconds_in_day
    dt_max = datetime.fromtimestamp(exp_target_max)
    

    headers = get_headers()
    params = {}
    params["symbol"] = symbol
    params["strikeCount"] = 200
    params["includeQuotes"] = True
    params["strategy"] = "ANALYTICAL"
    params["interval"] = 1
    params["fromDate"] = f"{dt_min.year}-{dt_min.month}-{dt_min.day}"
    params["toDate"] = f"{dt_max.year}-{dt_max.month}-{dt_max.day}"
    print(f"fromDate: {dt_min.year}-{dt_min.month}-{dt_min.day}")
    print(f"toDate: {dt_max.year}-{dt_max.month}-{dt_max.day}")
    params["daysToExpiration"] = 45
    req = "https://api.tdameritrade.com/v1/marketdata/chains"
    rsp = requests.get(req, params=params, headers=headers)
    if rsp.status_code != 200:
        print("got bad status code:", rsp.status_code)
        return None
    rsp_json = rsp.json()
    if rsp_json["status"] == "FAILED":
        print("got FAILED status")
        return None
    #print(rsp_json)
    return rsp_json

def get_contracts(chains):
    putMap = chains["putExpDateMap"]
    callMap = chains["callExpDateMap"]
    
    css_options = []
    cbs_options = []
    pss_options = []
    pbs_options = []
    num_calls = 0
    num_puts = 0
    
    expire_date = None
    for expDate in putMap:
        if expire_date:
            if expDate != expire_date:
                continue
        else:
            expire_date = expDate
        bundle = putMap[expDate]
        for strikePrice in bundle:
            options = bundle[strikePrice]
            for option in options:
                num_puts += 1
                description = option["description"]
                delta = option["delta"]
                strike = float(strikePrice)
                price = (option["bid"] + option["ask"])/2.0
                if  delta >= PSS_RANGE[0] and delta <= PSS_RANGE[1]:
                    pss_options.append({"description": description, "delta": delta, "strike": strike, "price": price})
                elif delta >= PBS_RANGE[0] and delta <= PBS_RANGE[1]:
                    pbs_options.append({"description": description, "delta": delta, "strike": strike, "price": price})
                else:
                    print(f"skip put option: {description} delta: {delta}")
    
    for expDate in callMap:
        if expire_date:
            if expDate != expire_date:
                continue
        else:
            expire_date = expDate
        bundle = callMap[expDate]
        for strikePrice in bundle:
            options = bundle[strikePrice]
            for option in options:
                num_calls += 1
                description = option["description"]
                delta = option["delta"]
                strike = float(strikePrice)
                price = (option["bid"] + option["ask"])/2.0
                if delta >= CSS_RANGE[0] and delta <= CSS_RANGE[1]:
                    css_options.append({"description": description, "delta": delta, "strike": strike, "price": price})
                elif delta >= CBS_RANGE[0] and delta <= CBS_RANGE[1]:
                    cbs_options.append({"description": description, "delta": delta, "strike": strike, "price": price})
                else:
                    print(f"skip call option: {description} delta: {delta}")
    
    print("num_puts:", num_puts)
    print("num_calls:", num_calls)
    total = len(css_options) + len(cbs_options) + len(pss_options) + len(pbs_options)
    print("total accepted:", total)
    print("contracts...")
    for contract_list in (css_options, cbs_options, pss_options, pbs_options):
        for contract in contract_list:
            description = contract["description"]
            strike = contract["strike"]
            delta = contract["delta"]
            price = contract["price"]
            print(f"{description} -- price: {price:.2f} strike: {strike:.2f} delta: {delta:.2f}")
        print("------")
    return {"css": css_options, "cbs": cbs_options, "pss": pss_options, "pbs": pbs_options}   


def get_candidates(contracts):
    candidates = []
    cs_list = contracts["css"]
    cb_list = contracts["cbs"]
    pb_list = contracts["pbs"]
    ps_list = contracts["pss"]
    for cs in cs_list:
        for cb in cb_list:
            for pb in pb_list:
                for ps in ps_list:
                    candidate = {"cs": cs, "cb": cb, "pb": pb, "ps": ps}
                    css = cs["strike"]
                    cbs = cb["strike"]
                    pbs = pb["strike"]
                    pss = ps["strike"]
                    csp = cs["price"]
                    cbp = cb["price"]
                    pbp = pb["price"]
                    psp = ps["price"]
                    csd = cs["delta"]
                    cbd = cb["delta"]
                    pbd = pb["delta"]
                    psd = ps["delta"]
                    if pss == pbs or cbs == css or pss == css:
                        print("strikes overlap, skipping")
                        continue
                    Tc = csp - cbp + psp - pbp
                    width = ((cbs - css) + (pss - pbs)) * 0.5
                    Tc_width = Tc / width
                    Etc = Tc * (1 - csd + psd) 
                    delta_cc = Tc * (csd - cbd)/(cbs - css)
                    delta_pc = Tc * (psd - pbd)/(pss - pbs) #-
                    delta_cd = csd - cbd - delta_cc
                    delta_pd = psd - pbd - delta_pc #-
                    Cd = cbs - css - Tc
                    Pd = pss - pbs - Tc
                    if Cd > Pd:
                        ml = Cd
                    else:
                        ml = Pd
                    Ecch = 0.5 * Tc * delta_cc
                    Epch = -0.5 * Tc * delta_pc
                    Ecdh = -0.5 * Cd * delta_cd #-
                    Epdh = 0.5 * Pd * delta_pd #-
                    Ecd = -Cd * cbd #-
                    Epd = Pd * pbd #-
                    Et = Etc + Ecch + Ecdh + Epch + Epdh + Ecd + Epd
                    Et_width = Et/width
                    Et_tc = Et/Tc
                    Et_ml = Et/ml
                    Tc_ml = Tc/ml
                    Et_tc = Et/Tc

                    candidate["Tc"] = Tc
                    candidate["width"] = width
                    candidate["Et"] = Et
                    candidate["Tc"] = Tc
                    candidate["Tc_width"] = Tc_width
                    candidate["Et_width"] = Et_width
                    candidate["Et_tc"] = Et_tc
                    candidate["ml"] = ml
                    candidate["Et_ml"] = Et_ml
                    candidate["Tc_ml"] = Tc_ml
                    candidate["Et_tc"] = Et_tc

                    """
                    print(f"==================")
                    print(f"{css:.3f}/{cbs:.3f}/{pss:.3f}/{pbs:.3f}")
                    """
                    """
                    print(f"csp: {csp:.3f}")
                    print(f"psp: {psp:.3f}")
                    print(f"cbp: {cbp:.3f}")
                    print(f"pbp: {pbp:.3f}")
                    print(f"Tc: {Tc:.3f}")
                    print(f"csd: {csd:.3f}")
                    print(f"psd: {psd:.3f}")
                    print(f"cbd: {cbd:.3f}")
                    print(f"pbd: {pbd:.3f}")                    
                    print(f"delta_cc: {delta_cc:.3f}")
                    print(f"delta_pc: {delta_pc:.3f}")
                    print(f"delta_cd: {delta_cd:.3f}")
                    print(f"delta_pd: {delta_pd:.3f}")
                    print(f"Cd: {Cd:.3f}")
                    print(f"Pd: {Pd:.3f}")
                    print(f"Ecch: {Ecch:.3f}")
                    print(f"Epch: {Epch:.3f}")
                    print(f"Ecdh: {Ecdh:.3f}")
                    print(f"Epdh: {Epdh:.3f}")      
                    print(f"Ecd: {Ecd:.3f}")
                    print(f"Epd: {Epd:.3f}")     
                    print(f"Etc: {Etc:.3f}") 
                    
                    
                    print(f"Et: {Et:.3f}")
                    print(f"Tc: {Tc:.3f}")
                    print(f"width: {width:.3f}")
                    print(f"ml: {ml:.3f}")
                    print(f"Tc/width: {Tc_width:.3f}")
                    print(f"Et/ml: {Et_ml:.3f}")
                    print(f"Et/width: {Et_width:.3f}")
                    print(f"Et/Tc: {Et/Tc:.3f}")
                    """

                    #if True or Et > 0.1 and Tc > width * 0.3334:                   
                    #if Et_width > 0.1 and Tc_width > 0.3334:
                    if Et > 3.5:
                        #print("adding candidate")
                        candidates.append(candidate)
    return candidates
        



#
# Main
#
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print("usage: python get_options.py SYM")
    sys.exit(1)
symbol = sys.argv[1]
print("getting symbol:", symbol)
chains = get_chains(symbol)
if not chains:
    sys.exit(1)
contracts = get_contracts(chains)

for k in contracts:
    options = contracts[k]
    print(k, len(options))
    for option in options:
        print(option["description"], option["delta"])

for k in contracts:
    options = contracts[k]
    if len(options) == 0:
        print("no candidates!")
        sys.exit(0)

print(f"got {len(contracts)} contracts")
candidates = get_candidates(contracts)
print("got", len(candidates), "candidates")
print("======================")

for key in ("Tc_ml", "Et", "Et_ml", "Tc_width", "Et_width", "Et_tc", "Tc"):
    candidates.sort(key = lambda candidate: candidate[key], reverse=True)
    rank = 1
    for candidate in candidates:
        candidate[key + "_rank"] = rank
        rank += 1


print("======================")

candidates.sort(key = lambda candidate: candidate["Et"], reverse=True)
rank = 1
for candidate in candidates:
    candidate["EtRank"] = rank
    rank += 1

printCandidates(candidates)

 

