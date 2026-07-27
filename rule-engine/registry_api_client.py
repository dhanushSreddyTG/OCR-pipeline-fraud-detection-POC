import re
from typing import Dict, Any

MOCK_REGISTRY_DATABASE = {
    "AADHAAR": {
        "366017829942": {
            "name": "SHASHIKANT WAKODE",
            "dob": "12-10-1995",
            "gender": "MALE",
            "status": "ACTIVE"
        }
    },
    "PAN": {
        "ABCPD1234F": {
            "name": "JOHN DOE",
            "dob": "01-01-1990",
            "status": "ACTIVE"
        }
    },
    "PASSPORT": {
        "A1234567": {
            "name": "JOHN DOE",
            "dob": "01-01-1990",
            "gender": "M",
            "status": "ACTIVE"
        }
    },
    "GST": {
        "29ABCDE1234F1Z5": {
            "legal_name": "ABC ENTERPRISES",
            "trade_name": "ABC SOLUTIONS",
            "status": "ACTIVE"
        }
    },
    "MCA": {
        "U72900KA2021PTC145678": {
            "company_name": "ACME TECHNOLOGIES PRIVATE LIMITED",
            "incorporation_date": "15-05-2021",
            "status": "ACTIVE"
        }
    },
    "CALIFORNIA": {
        "1234568": {
            "name": "IMA CARDHOLDER",
            "dob": "08/31/1977",
            "status": "ACTIVE",
            "class": "C"
        },
        "I1234568": {
            "name": "IMA CARDHOLDER",
            "dob": "08/31/1977",
            "status": "ACTIVE",
            "class": "C"
        }
    },
    "FLORIDA": {
        "S514-172-80-844-0": {
            "name": "JOE SAMPLE",
            "dob": "08-16-1960",
            "status": "ACTIVE",
            "class": "E"
        },
        "S514172808440": {
            "name": "JOE SAMPLE",
            "dob": "08-16-1960",
            "status": "ACTIVE",
            "class": "E"
        }
    },
    "INDIA": {
        "KA5920250004259": {
            "name": "DHANUSH REDDY S",
            "dob": "20-07-2005",
            "status": "ACTIVE"
        },
        "KA5120150002345": {
            "name": "GIRISH KUMAR",
            "dob": "12-10-1995",
            "status": "ACTIVE"
        },
        "MH0320180004567": {
            "name": "SHASHIKANT WAKODE",
            "dob": "15-06-1988",
            "status": "ACTIVE"
        },
        "DL1420190008901": {
            "name": "AMIT SHARMA",
            "dob": "22-11-1990",
            "status": "SUSPENDED"
        }
    }
}

class RegistryDatabaseClient:
    """
    Unified Mock Government & DMV Database API Client to check document authenticity.
    """

    @staticmethod
    def verify_aadhaar(aadhaar_number: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^0-9]", "", aadhaar_number)
        db = MOCK_REGISTRY_DATABASE["AADHAAR"]
        if clean_num in db:
            return {"found": True, "source": "UIDAI Aadhaar API", "record": db[clean_num]}
        return {"found": False, "source": "UIDAI Aadhaar API", "error": "AADHAAR_RECORD_NOT_FOUND"}

    @staticmethod
    def verify_pan(pan_number: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^A-Z0-9]", "", pan_number.upper())
        db = MOCK_REGISTRY_DATABASE["PAN"]
        if clean_num in db:
            return {"found": True, "source": "NSDL PAN API", "record": db[clean_num]}
        return {"found": False, "source": "NSDL PAN API", "error": "PAN_RECORD_NOT_FOUND"}

    @staticmethod
    def verify_passport(passport_number: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^A-Z0-9]", "", passport_number.upper())
        db = MOCK_REGISTRY_DATABASE["PASSPORT"]
        if clean_num in db:
            return {"found": True, "source": "Passport Seva API", "record": db[clean_num]}
        return {"found": False, "source": "Passport Seva API", "error": "PASSPORT_RECORD_NOT_FOUND"}

    @staticmethod
    def verify_gst(gstin: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^A-Z0-9]", "", gstin.upper())
        db = MOCK_REGISTRY_DATABASE["GST"]
        if clean_num in db:
            return {"found": True, "source": "GSTN Portal API", "record": db[clean_num]}
        return {"found": False, "source": "GSTN Portal API", "error": "GSTIN_RECORD_NOT_FOUND"}

    @staticmethod
    def verify_mca(cin: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^A-Z0-9]", "", cin.upper())
        db = MOCK_REGISTRY_DATABASE["MCA"]
        if clean_num in db:
            return {"found": True, "source": "MCA Portal API", "record": db[clean_num]}
        return {"found": False, "source": "MCA Portal API", "error": "CIN_RECORD_NOT_FOUND"}

    @staticmethod
    def verify_california_dl(dl_number: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^A-Z0-9]", "", dl_number.upper())
        db = MOCK_REGISTRY_DATABASE["CALIFORNIA"]
        for key, record in db.items():
            if re.sub(r"[^A-Z0-9]", "", key.upper()) == clean_num:
                return {"found": True, "source": "California DMV API", "record": record}
        return {"found": False, "source": "California DMV API", "error": "DL_RECORD_NOT_FOUND"}

    @staticmethod
    def verify_florida_dl(dl_number: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^A-Z0-9]", "", dl_number.upper())
        db = MOCK_REGISTRY_DATABASE["FLORIDA"]
        for key, record in db.items():
            if re.sub(r"[^A-Z0-9]", "", key.upper()) == clean_num:
                return {"found": True, "source": "Florida DHSMV API", "record": record}
        return {"found": False, "source": "Florida DHSMV API", "error": "DL_RECORD_NOT_FOUND"}

    @staticmethod
    def verify_indian_dl(dl_number: str) -> Dict[str, Any]:
        clean_num = re.sub(r"[^A-Z0-9]", "", dl_number.upper())
        db = MOCK_REGISTRY_DATABASE["INDIA"]
        for key, record in db.items():
            if re.sub(r"[^A-Z0-9]", "", key.upper()) == clean_num:
                return {"found": True, "source": "Indian Parivahan API", "record": record}
        return {"found": False, "source": "Indian Parivahan API", "error": "DL_RECORD_NOT_FOUND"}
