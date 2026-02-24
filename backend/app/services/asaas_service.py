import httpx
from app.core.config import settings


class AsaasService:
    def __init__(self):
        self.base_url = settings.ASAAS_BASE_URL
        self.headers = {
            "access_token": settings.ASAAS_API_KEY,
            "Content-Type": "application/json"
        }

    async def criar_cliente(self, nome: str, cpf_cnpj: str, email: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/customers",
                json={
                    "name": nome,
                    "cpfCnpj": cpf_cnpj,
                    "email": email,
                    "notificationDisabled": False
                },
                headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def criar_assinatura(
        self, customer_id: str, valor: float, ciclo: str = "MONTHLY", descricao: str = "FiscalSpy"
    ) -> dict:
        from datetime import date
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/subscriptions",
                json={
                    "customer": customer_id,
                    "billingType": "BOLETO",
                    "value": valor,
                    "nextDueDate": date.today().isoformat(),
                    "cycle": ciclo,
                    "description": descricao
                },
                headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    async def buscar_cliente_por_cnpj(self, cnpj: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/customers",
                params={"cpfCnpj": cnpj},
                headers=self.headers
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("data"):
                return data["data"][0]
            return None
