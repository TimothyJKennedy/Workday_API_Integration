import requests
import json
import base64
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='ap_integration.log'
)
logger = logging.getLogger('workday_integration')

class WorkdayAPIntegration:
    def __init__(self, tenant_url, client_id, client_secret):
        """
        Initialize the Workday integration with authentication credentials
        
        Args:
            tenant_url (str): Workday tenant URL (e.g., 'https://wd2-impl-services1.workday.com')
            client_id (str): OAuth client ID
            client_secret (str): OAuth client secret
        """
        self.tenant_url = tenant_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = None
    
    def get_auth_token(self):
        """Get OAuth token from Workday"""
        if self.token and self.token_expiry and self.token_expiry > datetime.now():
            return self.token
            
        auth_url = f"{self.tenant_url}/ccx/oauth2/token"
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": "workday_api"
        }
        
        try:
            response = requests.post(auth_url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            self.token = token_data['access_token']
            # Calculate token expiry (usually 1 hour)
            self.token_expiry = datetime.now().timestamp() + token_data['expires_in']
            
            return self.token
        except requests.RequestException as e:
            logger.error(f"Authentication error: {str(e)}")
            raise Exception(f"Failed to authenticate with Workday: {str(e)}")
    
    def create_invoice(self, invoice_data):
        """
        Create a supplier invoice in Workday
        
        Args:
            invoice_data (dict): Invoice details including supplier, amounts, and line items
            
        Returns:
            dict: The response from Workday with the created invoice details
        """
        token = self.get_auth_token()
        api_endpoint = f"{self.tenant_url}/api/v1/financial-management/suppliers/invoices"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Format the invoice data according to Workday's API requirements
        formatted_invoice = {
            "supplierReference": invoice_data["supplier_id"],
            "invoiceNumber": invoice_data["invoice_number"],
            "invoiceDate": invoice_data["invoice_date"],
            "invoiceDescription": invoice_data.get("description", ""),
            "invoiceTotal": {
                "amount": invoice_data["total_amount"],
                "currency": invoice_data.get("currency", "USD")
            },
            "invoiceLines": [
                {
                    "lineNumber": idx + 1,
                    "itemDescription": item.get("description", ""),
                    "amount": {
                        "amount": item["amount"],
                        "currency": invoice_data.get("currency", "USD")
                    },
                    "costCenter": item.get("cost_center", ""),
                    "projectReference": item.get("project_id", ""),
                    "accountCategory": item.get("account_category", "")
                }
                for idx, item in enumerate(invoice_data["line_items"])
            ]
        }
        
        try:
            response = requests.post(api_endpoint, headers=headers, json=formatted_invoice)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Successfully created invoice {invoice_data['invoice_number']} in Workday")
            return result
        except requests.RequestException as e:
            logger.error(f"Error creating invoice: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to create invoice in Workday: {str(e)}")
    
    def get_invoice_status(self, invoice_id):
        """
        Get the current status of an invoice in Workday
        
        Args:
            invoice_id (str): The Workday ID of the invoice
            
        Returns:
            dict: Invoice status information
        """
        token = self.get_auth_token()
        api_endpoint = f"{self.tenant_url}/api/v1/financial-management/suppliers/invoices/{invoice_id}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(api_endpoint, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error getting invoice status: {str(e)}")
            raise Exception(f"Failed to get invoice status from Workday: {str(e)}")
    
    def update_invoice_payment(self, invoice_id, payment_data):
        """
        Update an invoice with payment information
        
        Args:
            invoice_id (str): The Workday ID of the invoice
            payment_data (dict): Payment details
            
        Returns:
            dict: Updated invoice information
        """
        token = self.get_auth_token()
        api_endpoint = f"{self.tenant_url}/api/v1/financial-management/suppliers/invoices/{invoice_id}/payments"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        formatted_payment = {
            "paymentDate": payment_data["payment_date"],
            "paymentMethod": payment_data["payment_method"],
            "paymentAmount": {
                "amount": payment_data["amount"],
                "currency": payment_data.get("currency", "USD")
            },
            "paymentReference": payment_data.get("reference", "")
        }
        
        try:
            response = requests.put(api_endpoint, headers=headers, json=formatted_payment)
            response.raise_for_status()
            
            logger.info(f"Successfully updated payment for invoice {invoice_id}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error updating payment: {str(e)}")
            raise Exception(f"Failed to update invoice payment in Workday: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Configuration values (should be stored securely in production)
    WORKDAY_TENANT = "https://wd2-impl-services1.workday.com"
    CLIENT_ID = "your_client_id"
    CLIENT_SECRET = "your_client_secret"
    
    # Initialize the integration
    workday = WorkdayAPIntegration(WORKDAY_TENANT, CLIENT_ID, CLIENT_SECRET)
    
    # Example invoice data from the AP system
    invoice = {
        "supplier_id": "SUPP-001234",
        "invoice_number": "INV-2025-0012",
        "invoice_date": "2025-03-01",
        "description": "Office supplies for Q1",
        "total_amount": 1250.75,
        "currency": "USD",
        "line_items": [
            {
                "description": "Printer paper",
                "amount": 450.25,
                "cost_center": "CC-IT-001",
                "account_category": "OFFICE_SUPPLIES"
            },
            {
                "description": "Toner cartridges",
                "amount": 800.50,
                "cost_center": "CC-IT-001",
                "account_category": "OFFICE_SUPPLIES"
            }
        ]
    }
    
    try:
        # Create an invoice in Workday
        result = workday.create_invoice(invoice)
        invoice_id = result["id"]
        print(f"Created invoice with ID: {invoice_id}")
        
        # Check the status of the invoice
        status = workday.get_invoice_status(invoice_id)
        print(f"Invoice status: {status['approvalStatus']}")
        
        # Update with payment information
        payment = {
            "payment_date": "2025-03-15",
            "payment_method": "ACH",
            "amount": 1250.75,
            "currency": "USD",
            "reference": "PMT-2025-0089"
        }
        
        updated = workday.update_invoice_payment(invoice_id, payment)
        print(f"Updated invoice payment status: {updated['paymentStatus']}")
        
    except Exception as e:
        print(f"Integration error: {str(e)}")
