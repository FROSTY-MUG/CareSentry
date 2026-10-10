"""Drug ontology and alias reference table.

Versioned offline alias table seeded from RxNorm and WHO-ATC classification.
Version: 1.0.0
"""

from typing import Any, Dict, List

ONTOLOGY_VERSION = "1.0.0"

# Drug family definitions with canonical ingredients, classes, and aliases
# Must contain >= 150 alias entries across required families
DRUG_ONTOLOGY_REGISTRY: List[Dict[str, Any]] = [
    # 1. PENICILLIN FAMILY
    {
        "canonical_name": "penicillin",
        "drug_class": "penicillin",
        "rxcui": "70618",
        "atc_code": "J01CE01",
        "aliases": [
            "penicillin", "penicillin g", "penicillin v", "penicillin vk", "pen-vk",
            "pcn", "benzylpenicillin", "phenoxymethylpenicillin", "bicillin", "bicillin c-r",
            "bicillin l-a", "penicilline", "penicilin", "pencillin"
        ]
    },
    {
        "canonical_name": "amoxicillin",
        "drug_class": "penicillin",
        "rxcui": "723",
        "atc_code": "J01CA04",
        "aliases": [
            "amoxicillin", "amoxil", "moxatag", "amoxicilline", "amoxacillin",
            "amoxycillin", "amox", "trimox", "dispermox", "amoxicilina"
        ]
    },
    {
        "canonical_name": "amoxicillin/clavulanate",
        "drug_class": "penicillin",
        "rxcui": "18631",
        "atc_code": "J01CR02",
        "aliases": [
            "augmentin", "amoxicillin clavulanate", "amoxicillin and clavulanate potassium",
            "augmentin xr", "augmentin es-600", "clavulin", "amox-clav", "amox/clav",
            "co-amoxiclav", "amoxicillin-clavulanic acid"
        ]
    },
    {
        "canonical_name": "ampicillin",
        "drug_class": "penicillin",
        "rxcui": "733",
        "atc_code": "J01CA01",
        "aliases": [
            "ampicillin", "principen", "omnipen", "ampicilline", "ampicilina",
            "unasyn", "ampicillin/sulbactam", "ampicillin-sulbactam"
        ]
    },
    {
        "canonical_name": "piperacillin/tazobactam",
        "drug_class": "penicillin",
        "rxcui": "61678",
        "atc_code": "J01CR05",
        "aliases": [
            "zosyn", "piperacillin tazobactam", "pip-tazo", "pip/taz",
            "piperacillin and tazobactam", "tazocin", "piptazo"
        ]
    },
    {
        "canonical_name": "nafcillin",
        "drug_class": "penicillin",
        "rxcui": "7242",
        "atc_code": "J01CF06",
        "aliases": ["nafcillin", "unipen", "nallpen", "oxacillin", "bactocill", "dicloxacillin", "dynapen"]
    },

    # 2. SULFONAMIDE (SULFA) FAMILY
    {
        "canonical_name": "sulfamethoxazole/trimethoprim",
        "drug_class": "sulfonamide",
        "rxcui": "10180",
        "atc_code": "J01EE01",
        "aliases": [
            "bactrim", "bactrim ds", "septra", "septra ds", "tmp-smx", "smx-tmp",
            "trimethoprim-sulfamethoxazole", "sulfamethoxazole-trimethoprim", "co-trimoxazole",
            "cotrimoxazole", "sulfatrim", "smz-tmp", "tmp/smx", "smx/tmp"
        ]
    },
    {
        "canonical_name": "sulfadiazine",
        "drug_class": "sulfonamide",
        "rxcui": "10175",
        "atc_code": "J01EC02",
        "aliases": ["sulfadiazine", "silvadene", "silver sulfadiazine", "ssd cream", "thermazene"]
    },
    {
        "canonical_name": "sulfasalazine",
        "drug_class": "sulfonamide",
        "rxcui": "10183",
        "atc_code": "A07EC01",
        "aliases": ["sulfasalazine", "azulfidine", "azulfidine en-tabs", "salazopyrin", "sulfa"]
    },
    {
        "canonical_name": "sulfisoxazole",
        "drug_class": "sulfonamide",
        "rxcui": "10187",
        "atc_code": "J01EB02",
        "aliases": ["sulfisoxazole", "gantrisin", "truxazole", "sulfa allergy", "sulphonamide"]
    },

    # 3. NSAID FAMILY
    {
        "canonical_name": "ibuprofen",
        "drug_class": "nsaid",
        "rxcui": "5640",
        "atc_code": "M01AE01",
        "aliases": [
            "ibuprofen", "advil", "motrin", "motrin ib", "nuprin", "caldolor",
            "ibuprofin", "ibuprophen", "brufen", "pediaprofen", "ibu"
        ]
    },
    {
        "canonical_name": "naproxen",
        "drug_class": "nsaid",
        "rxcui": "7258",
        "atc_code": "M01AE02",
        "aliases": [
            "naproxen", "aleve", "naprosyn", "anaprox", "anaprox ds", "flanax",
            "naprelan", "naproxen sodium"
        ]
    },
    {
        "canonical_name": "ketorolac",
        "drug_class": "nsaid",
        "rxcui": "6142",
        "atc_code": "M01AB15",
        "aliases": ["ketorolac", "toradol", "sprix", "ketorolac tromethamine", "tromethamine"]
    },
    {
        "canonical_name": "meloxicam",
        "drug_class": "nsaid",
        "rxcui": "214199",
        "atc_code": "M01AC06",
        "aliases": ["meloxicam", "mobic", "vivlodex", "qmiiz", "qmiiz odt"]
    },
    {
        "canonical_name": "celecoxib",
        "drug_class": "nsaid",
        "rxcui": "214354",
        "atc_code": "M01AH01",
        "aliases": ["celecoxib", "celebrex", "elyxyb", "cox-2 inhibitor"]
    },
    {
        "canonical_name": "aspirin",
        "drug_class": "nsaid",
        "rxcui": "1191",
        "atc_code": "B01AC06",
        "aliases": [
            "aspirin", "acetylsalicylic acid", "asa", "bayer aspirin", "ecotrin",
            "bufferin", "baby aspirin", "st joseph aspirin", "empirin"
        ]
    },
    {
        "canonical_name": "diclofenac",
        "drug_class": "nsaid",
        "rxcui": "3355",
        "atc_code": "M01AB05",
        "aliases": [
            "diclofenac", "voltaren", "voltaren gel", "cataflam", "zipsor",
            "cambia", "zorvolex", "diclofenac sodium"
        ]
    },
    {
        "canonical_name": "indomethacin",
        "drug_class": "nsaid",
        "rxcui": "5807",
        "atc_code": "M01AB01",
        "aliases": ["indomethacin", "indocin", "tivorbex", "indocid"]
    },

    # 4. METFORMIN FAMILY
    {
        "canonical_name": "metformin",
        "drug_class": "biguanide",
        "rxcui": "6809",
        "atc_code": "A10BA02",
        "aliases": [
            "metformin", "glucophage", "glucophage xr", "fortamet", "glumetza",
            "riomet", "metformin hydrochloride", "metformin hcl", "metformin er",
            "metforim", "metformina"
        ]
    },
    {
        "canonical_name": "metformin/sitagliptin",
        "drug_class": "biguanide",
        "rxcui": "692440",
        "atc_code": "A10BD07",
        "aliases": ["janumet", "janumet xr", "sitagliptin and metformin", "sitagliptin-metformin"]
    },
    {
        "canonical_name": "metformin/empagliflozin",
        "drug_class": "biguanide",
        "rxcui": "1658428",
        "atc_code": "A10BD20",
        "aliases": ["synjardy", "synjardy xr", "empagliflozin and metformin"]
    },

    # 5. SPIRONOLACTONE FAMILY
    {
        "canonical_name": "spironolactone",
        "drug_class": "aldosterone_antagonist",
        "rxcui": "9997",
        "atc_code": "C03DA01",
        "aliases": [
            "spironolactone", "aldactone", "carospir", "spirono", "aldactazide",
            "spiractin", "spironolacton", "spironolactona"
        ]
    },
    {
        "canonical_name": "eplerenone",
        "drug_class": "aldosterone_antagonist",
        "rxcui": "285888",
        "atc_code": "C03DA04",
        "aliases": ["eplerenone", "inspra"]
    },

    # 6. ANTICOAGULANT FAMILY
    {
        "canonical_name": "warfarin",
        "drug_class": "anticoagulant",
        "rxcui": "11289",
        "atc_code": "B01AA03",
        "aliases": [
            "warfarin", "coumadin", "jantoven", "warfarin sodium", "marevan",
            "warfarinum", "warfarina"
        ]
    },
    {
        "canonical_name": "apixaban",
        "drug_class": "anticoagulant",
        "rxcui": "1364430",
        "atc_code": "B01AF02",
        "aliases": ["apixaban", "eliquis", "factor xa inhibitor", "apixiban"]
    },
    {
        "canonical_name": "rivaroxaban",
        "drug_class": "anticoagulant",
        "rxcui": "1114195",
        "atc_code": "B01AF01",
        "aliases": ["rivaroxaban", "xarelto", "rivaroxiban"]
    },
    {
        "canonical_name": "dabigatran",
        "drug_class": "anticoagulant",
        "rxcui": "1009140",
        "atc_code": "B01AE07",
        "aliases": ["dabigatran", "pradaxa", "dabigatran etexilate"]
    },
    {
        "canonical_name": "heparin",
        "drug_class": "anticoagulant",
        "rxcui": "5224",
        "atc_code": "B01AB01",
        "aliases": ["heparin", "unfractionated heparin", "ufh", "heparin sodium"]
    },
    {
        "canonical_name": "enoxaparin",
        "drug_class": "anticoagulant",
        "rxcui": "67108",
        "atc_code": "B01AB05",
        "aliases": ["enoxaparin", "lovenox", "clexane", "low molecular weight heparin", "lmwh"]
    },

    # 7. CEPHALOSPORIN FAMILY (CROSS-REACTIVITY MAPPING)
    {
        "canonical_name": "cephalexin",
        "drug_class": "cephalosporin_1st_gen",
        "rxcui": "2231",
        "atc_code": "J01DB01",
        "aliases": ["cephalexin", "keflex", "cefalexin", "keflet", "keftab"]
    },
    {
        "canonical_name": "cefazolin",
        "drug_class": "cephalosporin_1st_gen",
        "rxcui": "2180",
        "atc_code": "J01DB04",
        "aliases": ["cefazolin", "ancef", "kefzol"]
    },
    {
        "canonical_name": "ceftriaxone",
        "drug_class": "cephalosporin_3rd_gen",
        "rxcui": "2193",
        "atc_code": "J01DD04",
        "aliases": ["ceftriaxone", "rocephin", "ceftriaxone sodium"]
    },
    {
        "canonical_name": "cefepime",
        "drug_class": "cephalosporin_4th_gen",
        "rxcui": "235473",
        "atc_code": "J01DE01",
        "aliases": ["cefepime", "maxipime"]
    },

    # 8. GERIATRIC / HIGH ANTICHOLINERGIC BURDEN DRUGS (BEERS CRITERIA)
    {
        "canonical_name": "diphenhydramine",
        "drug_class": "anticholinergic_antihistamine",
        "rxcui": "3498",
        "atc_code": "R06AA02",
        "aliases": ["diphenhydramine", "benadryl", "sominex", "unisom", "dph"]
    },
    {
        "canonical_name": "hydroxyzine",
        "drug_class": "anticholinergic_antihistamine",
        "rxcui": "5553",
        "atc_code": "N05BB01",
        "aliases": ["hydroxyzine", "atarax", "vistaril"]
    },
    {
        "canonical_name": "amitriptyline",
        "drug_class": "tricyclic_antidepressant",
        "rxcui": "704",
        "atc_code": "N06AA09",
        "aliases": ["amitriptyline", "elavil", "endep", "vanatrip"]
    },
    {
        "canonical_name": "oxybutynin",
        "drug_class": "anticholinergic_urological",
        "rxcui": "7715",
        "atc_code": "G04BD04",
        "aliases": ["oxybutynin", "ditropan", "ditropan xl", "oxytrol", "gelnique"]
    },
    {
        "canonical_name": "diazepam",
        "drug_class": "benzodiazepine",
        "rxcui": "3322",
        "atc_code": "N05BA01",
        "aliases": ["diazepam", "valium", "diastat"]
    },
    {
        "canonical_name": "lorazepam",
        "drug_class": "benzodiazepine",
        "rxcui": "6470",
        "atc_code": "N05BA06",
        "aliases": ["lorazepam", "ativan"]
    },
    {
        "canonical_name": "alprazolam",
        "drug_class": "benzodiazepine",
        "rxcui": "596",
        "atc_code": "N05BA12",
        "aliases": ["alprazolam", "xanax", "niravam"]
    },
    {
        "canonical_name": "clopidogrel",
        "drug_class": "antiplatelet",
        "rxcui": "32968",
        "atc_code": "B01AC04",
        "aliases": ["clopidogrel", "plavix"]
    },
    {
        "canonical_name": "omeprazole",
        "drug_class": "proton_pump_inhibitor",
        "rxcui": "7646",
        "atc_code": "A02BC01",
        "aliases": ["omeprazole", "prilosec", "prilosec otc", "zegerid"]
    },
    {
        "canonical_name": "lisinopril",
        "drug_class": "ace_inhibitor",
        "rxcui": "29046",
        "atc_code": "C09AA03",
        "aliases": ["lisinopril", "prinivil", "zestril", "qbrelis"]
    }
]
