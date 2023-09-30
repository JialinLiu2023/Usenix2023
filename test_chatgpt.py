import os
import openai
# openai.organization = "Personal"
openai.api_key_path = "../openai_auth.txt"
print(openai.Model.list())

