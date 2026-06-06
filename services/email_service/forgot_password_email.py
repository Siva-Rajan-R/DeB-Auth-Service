
def generate_forgot_password_email_content(reset_link: str, brand_name: str = "DeB-Auth") -> str:
    return f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
    <div style="max-width: 500px; margin: auto; background: #ffffff; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); padding: 30px; text-align: center;">
      
      <h2 style="color: #333333;">Reset Your Password</h2>
      
      <p style="font-size: 16px; color: #555555;">
        We received a request to reset your password for your <strong>{brand_name}</strong> account.
      </p>
      
      <div style="margin: 30px 0;">
        <a href="{reset_link}" 
           style="display: inline-block; font-size: 16px; font-weight: bold; color: #ffffff; background: linear-gradient(90deg, #4f46e5, #7c3aed); padding: 15px 35px; border-radius: 8px; text-decoration: none;">
          Reset Password
        </a>
      </div>
      
      <p style="font-size: 14px; color: #999999;">
        This link will expire in 15 minutes. If you didn't request this, you can safely ignore this email.
      </p>
      
      <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;" />
      
      <p style="font-size: 12px; color: #cccccc;">
        If the button doesn't work, copy and paste this link into your browser:<br/>
        <a href="{reset_link}" style="color: #4f46e5; word-break: break-all;">{reset_link}</a>
      </p>
      
    </div>
  </body>
</html>
"""
