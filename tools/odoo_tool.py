import os
from dotenv import load_dotenv
import odoorpc
from langchain.tools import BaseTool
from pydantic import PrivateAttr, BaseModel, Field
from typing import Optional, List, Dict, Any, Type

class OdooToolInput(BaseModel):
    action: str = Field(description="Action to perform: list, count, schema, create, update, delete")
    model: str = Field(description="Odoo model name")
    domain: Optional[list] = Field(default_factory=list, description="Odoo domain filter")
    fields: Optional[list] = Field(default_factory=list, description="Fields to fetch")
    values: Optional[dict] = Field(default_factory=dict, description="Values for create/update")
    ids: Optional[list] = Field(default_factory=list, description="Record IDs for update/delete")

class OdooTool(BaseTool):

    """A tool to interact with Odoo."""

    name: str = "odoo_tool"
    description: str = "A tool to interact with Odoo."
    args_schema: Type[BaseModel] = OdooToolInput

    _odoo: odoorpc.ODOO = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)

        load_dotenv()
        odoo_url = os.getenv('ODOO_HOST')
        odoo_port = int(os.getenv('ODOO_PORT', '8069'))
        db = os.getenv('ODOO_DB')
        username = os.getenv('ODOO_USER')
        password = os.getenv('ODOO_PASSWORD')
        print(f"Connecting to Odoo at {odoo_url}:{odoo_port} with database {db} and user {username}")
        self._odoo = odoorpc.ODOO(host=odoo_url, port=odoo_port, protocol='jsonrpc')
        # if not self._odoo.is_connected():
        #     if not db or not username or not password:
        #         raise ValueError("Odoo connection requires ODOO_DB, ODOO_USER, and ODOO_PASSWORD environment variables.")
        self._odoo.login(db, username, password)

    def _run(self,
        action: str,
        model: str,
        domain: list = None,
        fields: list = None,
        values: dict = None,
        ids: list = None,
        **kwargs
    ):
        """
        Run the Odoo tool with the specified action and parameters.
        :param action:
        :param model:
        :param domain:
        :param fields:
        :param values:
        :param ids:
        :param kwargs:
        :return:
        """

        Model = self._odoo.env[model]
        domain = domain or []
        fields = fields or []
        values = values or {}
        ids = ids or []

        if action == "list":
            return Model.search_read(domain, fields)
        elif action == "count":
            return Model.search_count(domain)
        elif action == "schema":
            return Model.fields_get()
        elif action == "create":
            return Model.create(values)
        elif action == "update":
            return Model.write(ids, values)
        elif action == "delete":
            return Model.unlink(ids)
        else:
            return {"error": f"Unknown action: {action}"}
