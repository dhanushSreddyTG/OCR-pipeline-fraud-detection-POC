import re
from datetime import datetime
from base import BaseRule

class USBankStatementRules(BaseRule):
    def __init__(self):
        super().__init__("US Bank Statement")
        self.verification_method = "Arithmetic Balance Audit"

    def evaluate(self, data: dict, full_text: str, lines: list, font_info: dict, file_path: str = None) -> dict:
        self.flags = []
        self.points = 0

        doc_type = data.get("document_type", "US Bank Statement")
        self.evaluate_document_colors(file_path, doc_type)

        beg_bal = data.get("beginning_balance")
        end_bal = data.get("ending_balance")
        deposits = data.get("total_deposits")
        withdrawals = data.get("total_withdrawals")

        # 1. Statement Balance Sheet Math Verification
        if beg_bal is not None and end_bal is not None and deposits is not None and withdrawals is not None:
            # Note: total_withdrawals is typically stored as a negative number in our processor
            expected_end = beg_bal + deposits + withdrawals
            diff = abs(end_bal - expected_end)
            if diff > 0.05:
                self.add_flag(
                    "STATEMENT_BALANCE_MISMATCH",
                    f"Financial summary balance mismatch! Beginning Balance ({beg_bal}) + Deposits ({deposits}) + Withdrawals ({withdrawals}) = {expected_end:.2f}, but Ending Balance is reported as {end_bal} (Difference: {diff:.2f}).",
                    "High",
                    50
                )

        # 2. Transaction Flow Verification
        transactions = data.get("transactions", [])
        if transactions:
            current_balance = beg_bal
            mismatch_count = 0
            for idx, tx in enumerate(transactions):
                credits = tx.get("credits", 0.0)
                debits = tx.get("debits", 0.0)
                reported_bal = tx.get("balance")

                if current_balance is not None and reported_bal is not None:
                    # In some statements debits are negative, in others they are positive. We handle both.
                    expected_bal1 = current_balance + credits + debits
                    expected_bal2 = current_balance + credits - abs(debits)
                    
                    diff1 = abs(reported_bal - expected_bal1)
                    diff2 = abs(reported_bal - expected_bal2)
                    
                    if diff1 > 0.05 and diff2 > 0.05:
                        mismatch_count += 1
                    
                    # Update running balance
                    current_balance = reported_bal
            
            if mismatch_count > 0:
                self.add_flag(
                    "TRANSACTION_FLOW_MISMATCH",
                    f"Detected {mismatch_count} balance deviations within the transaction history ledger.",
                    "High",
                    45
                )
        else:
            self.add_flag("MISSING_TRANSACTIONS", "No transaction activity rows detected on the bank statement.", "Medium", 20)

        # 3. Future Statement Date Check
        stmt_date = data.get("statement_date")
        if stmt_date:
            dt = self.parse_date(stmt_date)
            if dt and dt > datetime.now():
                self.add_flag("STATEMENT_FUTURE_DATE", f"Statement Date '{stmt_date}' cannot be in the future.", "High", 40)

        # 4. Account Details Checks
        acc_no = data.get("account_number")
        if not acc_no:
            self.add_flag("MISSING_ACCOUNT_NUMBER", "Account Number is missing from the bank statement.", "Medium", 15)

        return {
            "flags": self.flags,
            "points": min(100, self.points)
        }
