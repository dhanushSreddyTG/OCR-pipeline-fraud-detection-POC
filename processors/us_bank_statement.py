import re
from typing import Dict, Any, List
from .base import BaseDocumentProcessor

class USBankStatementProcessor(BaseDocumentProcessor):
    def parse(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "US Bank Statement",
            "bank_name": "Ally Bank",
            "customer_name": None,
            "statement_date": None,
            "account_number": None,
            "open_date": None,
            "product": None,
            "beginning_balance": None,
            "ending_balance": None,
            "total_deposits": None,
            "total_withdrawals": None,
            "interest_paid_ytd": None,
            "interest_paid_period": None,
            "average_daily_balance": None,
            "transactions": []
        }

        # Helper to convert dollar strings to floats
        def to_float(val_str: str) -> float:
            if not val_str:
                return 0.0
            cleaned = re.sub(r"[^\d.-]", "", val_str)
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        # 1. Bank Name
        if "ally" in text.lower():
            data["bank_name"] = "Ally Bank"

        # 2. Customer Name (Summary For: John Citizen)
        cust_match = re.search(r"Summary\s+For\s*:\s*([A-Za-z\s]+)", text, re.IGNORECASE)
        if cust_match:
            data["customer_name"] = cust_match.group(1).strip()

        # 3. Statement Date
        date_match = re.search(r"Statement\s+Date\s*[\r\n]*\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
        if date_match:
            data["statement_date"] = date_match.group(1)

        # 4. Account Number (Account Number: xxxxxx7583)
        acc_match = re.search(r"Account\s+Number\s*:\s*([A-Za-z0-9xX]+)", text, re.IGNORECASE)
        if acc_match:
            data["account_number"] = acc_match.group(1).strip()

        # 5. Open Date (Open Date: 12/06/2021)
        open_match = re.search(r"Open\s+Date\s*:\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if open_match:
            data["open_date"] = open_match.group(1)

        # 6. Product
        prod_match = re.search(r"Product\s*:\s*([A-Za-z\s]+Account|[A-Za-z\s]+Savings)", text, re.IGNORECASE)
        if prod_match:
            data["product"] = prod_match.group(1).strip()

        # 7. Balances and summaries
        # Beginning Balance, as of 03/06/2021 $4,182.88
        beg_match = re.search(r"Beginning\s+Balance\s*,\s*as\s+of\s+\d{2}/\d{2}/\d{4}\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if beg_match:
            data["beginning_balance"] = to_float(beg_match.group(1))

        # Ending Balance, as of 04/05/2021 $5,423.55
        end_match = re.search(r"Ending\s+Balance\s*,\s*as\s+of\s+\d{2}/\d{2}/\d{4}\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if not end_match:
            end_match = re.search(r"lEnding\s+Balance\s*,\s*as\s+of\s+\d{2}/\d{2}/\d{4}\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if end_match:
            data["ending_balance"] = to_float(end_match.group(1))

        # Deposits and Other Credits $4,013.63
        dep_match = re.search(r"Deposits\s+and\s+Other\s+Credits\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if not dep_match:
            dep_match = re.search(r"lbeposts\s+and\s+Other\s+Credits\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if dep_match:
            data["total_deposits"] = to_float(dep_match.group(1))

        # Withdrawals and Other Debits -$2,759.33
        with_match = re.search(r"Withdrawals\s+and\s+Other\s+Debits\s*(-?\$[\d,.-]+)", text, re.IGNORECASE)
        if not with_match:
            with_match = re.search(r"twthdrawat\s+and\s+Other\s+Debits\s*(-?\$[\d,.-]+)", text, re.IGNORECASE)
        if with_match:
            data["total_withdrawals"] = to_float(with_match.group(1))

        # Interest Paid This Period $3.63
        int_match = re.search(r"Interest\s+Paid\s+This\s+Period\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if not int_match:
            int_match = re.search(r"Interest\s+Paid\s+This\s+Peric\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if int_match:
            data["interest_paid_period"] = to_float(int_match.group(1))

        # Interest Paid Year to Date $6.40
        int_ytd_match = re.search(r"Interest\s+Paid\s+Year\s+to\s+Date\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if int_ytd_match:
            data["interest_paid_ytd"] = to_float(int_ytd_match.group(1))

        # Average Daily Balance This Period $4,774.74
        avg_match = re.search(r"Average\s+Daily\s+Balance\s+This\s+Peric\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if not avg_match:
            avg_match = re.search(r"Average\s+Daily\s+Balance\s+This\s+Period\s*(\$[\d,.-]+)", text, re.IGNORECASE)
        if avg_match:
            data["average_daily_balance"] = to_float(avg_match.group(1))

        # 8. Activity / Transactions table parsing
        # Each transaction starts with a date like 03/06/2021
        date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{4})\b")
        
        for line in full_text_lines:
            line_str = line.strip()
            # If the line starts with a date and is not "Beginning Balance" or "Ending Balance"
            m = date_pattern.match(line_str)
            if m:
                tx_date = m.group(1)
                # Skip summary balance lines in the activity table
                if "Beginning Balance" in line_str or "Ending Balance" in line_str:
                    continue
                
                # Parse description, credits, debits, balance
                # Try finding amounts in the line: e.g. $0.00 -$513.00
                amounts = re.findall(r"(-?\$[\d,]+\.\d{2})", line_str)
                
                # Description is everything in between date and amounts, plus the trailing text
                # E.g. "03/06/2021 ATM Withdrawal $0.00 -$513.00 BANCO POPULAR ..."
                # Let's extract clean descriptions
                desc = line_str[10:].strip()
                for amt in amounts:
                    desc = desc.replace(amt, "")
                desc = re.sub(r"\s+", " ", desc).strip()
                
                # Clean up description (like removing trailing Transaction Fee, etc.)
                if "Transaction Fee:" in desc:
                    desc = desc.split("Transaction Fee:")[0].strip()
                
                credits_val = 0.0
                debits_val = 0.0
                balance_val = None
                
                if len(amounts) >= 3:
                    credits_val = to_float(amounts[0])
                    debits_val = to_float(amounts[1])
                    balance_val = to_float(amounts[2])
                elif len(amounts) == 2:
                    val1 = to_float(amounts[0])
                    val2 = to_float(amounts[1])
                    if val1 > 0:
                        credits_val = val1
                    else:
                        debits_val = val1
                    balance_val = val2
                elif len(amounts) == 1:
                    val = to_float(amounts[0])
                    balance_val = val

                if desc:
                    # Clean trailing/leading non-word characters from description
                    desc = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9)]+$", "", desc).strip()
                    data["transactions"].append({
                        "date": tx_date,
                        "description": desc,
                        "credits": credits_val,
                        "debits": debits_val,
                        "balance": balance_val
                    })

        return data
