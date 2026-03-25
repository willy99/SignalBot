import pytest

from dics.deserter_xls_dic import *
from domain.notif_doc import NotifDoc
from service.constants import DB_TABLE_NOTIF_DOC, DOC_STATUS_COMPLETED
from service.docworkflow.BaseDocumentService import BaseDocumentService
from service.processing.processors.ExcelProcessor import ExcelProcessor
from tests.conftest import mock_db, mock_ctx
from tests.test_tools import generate_test_records
from domain.person_filter import PersonSearchFilter, YES
from utils.utils import format_to_excel_date
from datetime import datetime

def test_full_notification_cycle(mock_db, mock_ctx):
    # Тепер mock_db вже має всі таблиці з schema.sql
    service = BaseDocumentService(mock_db, mock_ctx, DB_TABLE_NOTIF_DOC, NotifDoc)

    # Створюємо документ
    new_doc = NotifDoc(region="Одеська", payload=[{'name': 'Тестовий'}])
    doc_id = service.save_doc(new_doc)

    # Перевіряємо
    assert service.get_doc_by_id(doc_id).region == "Одеська"



def test_notification_send(temp_excel_file, mock_logger, mock_db, mock_ctx):
    """Тестуємо вставку 20 записів та пошук по них"""
    service = BaseDocumentService(mock_db, mock_ctx, DB_TABLE_NOTIF_DOC, NotifDoc)
    processor = ExcelProcessor(temp_excel_file, mock_logger, is_test_mode=True)

    test_data = generate_test_records(20)

    try:
        success = processor.upsert_record(test_data)
        assert success is True

        target_name = test_data[0][COLUMN_NAME].split()[0]
        target_rnokpp = test_data[0][COLUMN_ID_NUMBER]
        des_region = test_data[0][COLUMN_DESERTION_REGION]

        print('>>> target nane')

        from domain.person_filter import PersonSearchFilter

        filter_obj = PersonSearchFilter(
            review_statuses=REVIEW_STATUS_MAP[REPORT_REVIEW_STATUS_NON_ERDR],
            empty_kpp=YES,
            desertion_region=des_region,
            include_402=False
        )

        results = processor.search_people(filter_obj)
        assert len(results) >= 1
        assert target_name in results[0]['data'][COLUMN_NAME]
        print('>>>> result = ' + str(results))

        payload = []
        for result in results:
            data = result['data']
            payload.append({
                'rnokpp': data[COLUMN_ID_NUMBER],
                'name': data[COLUMN_NAME],
                'desertion_date': data[COLUMN_DESERTION_DATE],
                'desertion_region': data[COLUMN_DESERTION_REGION]
            })

        new_doc = NotifDoc(
            region=des_region,
            out_number="642/4455",
            out_date=format_to_excel_date(datetime.now()),
            payload=payload
        )

        # 4. ЗБЕРЕЖЕННЯ (Insert)

        print('>>> doc ' + str(new_doc))


        doc_id = service.save_doc(new_doc)
        assert doc_id > 0, "Документ не був збережений (ID не отримано)"

        # 5. ПЕРЕВІРКА ЧИТАННЯ (Get)
        saved_doc = service.get_doc_by_id(doc_id)
        assert saved_doc is not None
        assert saved_doc.region == des_region
        assert len(saved_doc.payload) >= 1
        assert saved_doc.payload[0]['name'] == results[0]['data'][COLUMN_NAME]
        assert saved_doc.created_by == mock_ctx.user_id

        # 6. ОНОВЛЕННЯ (Update / Mark as completed)
        service.mark_as_completed(doc_id)

        updated_doc = service.get_doc_by_id(doc_id)
        assert updated_doc.status == DOC_STATUS_COMPLETED
        assert updated_doc.out_number == "642/4455"

        # 7. ВИДАЛЕННЯ (Soft Delete)
        service.delete_doc(doc_id)
        assert service.get_doc_by_id(doc_id) is None, "Документ не повинен знаходитись після видалення"
    finally:
        processor.close()

