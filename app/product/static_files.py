"""Explicit ES-module MIME independent of Windows registry associations."""
from fastapi.staticfiles import StaticFiles


class StudioStaticFiles(StaticFiles):
    async def get_response(self,path,scope):
        response=await super().get_response(path,scope)
        if path.lower().endswith('.mjs') and response.status_code in {200,206,304}:
            response.headers['content-type']='text/javascript; charset=utf-8'
        return response
