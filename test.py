# from fastapi_testrunner import TestFastAPIRoutes,CustomInputFormat

# test=TestFastAPIRoutes(
#     custom_input=CustomInputFormat(
#         method="post",
#         path="/auth",
#         isfor_json=True,
#         isfor_params=False,
#         data={'apikey':'DeB-hgDOF7xgIytpII36f_SUJO8aZXTAzOZRP0T2kDZTTZE'}
#     ),
#     routes_tocheck=['/auth']
# )
# test.start_test()

from secrets import token_urlsafe

print(token_urlsafe(64))
    
# 2401:4900:2346:e0ac:1:1:3976:2a26
# 2409:408d:3c05:1061:286d:548e:737:4702

