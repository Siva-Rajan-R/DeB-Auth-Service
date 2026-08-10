import razorpay
from icecream import ic
from configs.settings import settings

RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET

def get_razorpay_client():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        ic("WARNING: Razorpay keys not found or are mock keys. Billing features will run in mock mode.")
        return None
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_order(amount: float, currency: str = "INR", receipt: str = None):
    client = get_razorpay_client()
    if not client:
        # Mock order
        return {"id": f"order_mock_{receipt}", "amount": amount * 100, "currency": currency}
    
    data = {
        "amount": int(amount * 100), # Razorpay expects paise
        "currency": currency,
        "receipt": receipt
    }
    try:
        order = client.order.create(data=data)
        return order
    except Exception as e:
        ic(f"Razorpay order creation failed: {e}")
        return None

def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str):
    client = get_razorpay_client()
    if not client:
        return True # Mock success
    
    try:
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        return client.utility.verify_payment_signature(params_dict)
    except Exception as e:
        ic(f"Razorpay signature verification failed: {e}")
        return False
