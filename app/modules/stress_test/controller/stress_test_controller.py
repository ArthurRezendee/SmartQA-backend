from app.modules.stress_test.service.stress_test_service import StressTestService


class StressTestController:

    def __init__(self):
        self.service = StressTestService()

    async def create(self, db, target_id: int, user_id: int):
        return await self.service.create(db, target_id, user_id)

    async def get(self, db, stress_test_id: int, user_id: int):
        return await self.service.get_or_fail(db, stress_test_id, user_id)

    async def list_by_target(self, db, target_id: int, user_id: int):
        return await self.service.list_by_target(db, target_id, user_id)

    async def delete(self, db, stress_test_id: int, user_id: int):
        return await self.service.delete(db, stress_test_id, user_id)

    async def export_report(self, db, stress_test_id: int, user_id: int) -> bytes:
        from app.modules.export.service.pdf_service import PDFService
        st = await self.service.get_or_fail(db, stress_test_id, user_id)
        md = self.service.generate_report_markdown(st)
        return PDFService().generate_pdf(md, "md")
