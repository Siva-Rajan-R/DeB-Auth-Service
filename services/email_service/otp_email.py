
def generate_otp_email_content(otp: str) -> str:
    return  f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
    <div style="max-width: 500px; margin: auto; background: #ffffff; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); padding: 30px; text-align: center;">
      
      <h2 style="color: #333333;">Your OTP Code</h2>
      
      <p style="font-size: 16px; color: #555555;">Use the code below to verify your account. It’s valid for a single use only.</p>
      
      <div style="margin: 30px 0;">
        <span style="font-size: 32px; font-weight: bold; color: #ffffff; background: linear-gradient(90deg, #4CAF50, #81C784); padding: 15px 25px; border-radius: 8px; letter-spacing: 5px;">{otp}</span>
      </div>
      
      <p style="font-size: 14px; color: #999999;">Please do not share this OTP with anyone. If you didn't request this, ignore this email.</p>
      
    </div>
  </body>
</html>
"""
