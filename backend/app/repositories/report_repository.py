from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.extensions import db
from app.models import MedicalReport, ReportIndicator, User


def _now(): return datetime.now().replace(microsecond=0)
def _date(value): return value if isinstance(value,date) else datetime.strptime(str(value),"%Y-%m-%d").date()
def _datetime(value):
    if isinstance(value,datetime): return value.replace(tzinfo=None)
    return datetime.fromisoformat(str(value)).replace(tzinfo=None) if value else None
def _number(value): return float(value) if isinstance(value,Decimal) else value


class ReportRepository:
    @staticmethod
    def detail(row):
        return {"id":row.id,"file_name":row.file_name,"file_type":row.file_type,"report_date":row.report_date.isoformat(),"status":row.status,"confidence":_number(row.confidence),"summary":row.summary or "","created_at":row.uploaded_at.isoformat()}

    @staticmethod
    def get(report_id,user_id=1): return MedicalReport.query.filter_by(id=report_id,user_id=user_id).one_or_none()

    @classmethod
    def upload(cls,file_name,file_type,source,report_date,file_url,user_id=1):
        row=MedicalReport(user_id=user_id,file_name=file_name,file_type=file_type,file_url=file_url,source=source or file_type,report_date=_date(report_date),status="uploaded",progress=0,uploaded_at=_now())
        db.session.add(row);db.session.commit()
        return {"report_id":row.id,"file_name":row.file_name,"file_type":row.file_type,"status":row.status,"progress":row.progress}

    @classmethod
    def start(cls,report_id,user_id=1):
        row=cls.get(report_id,user_id)
        if not row:return None
        row.status="recognizing";row.progress=10;row.confidence=None;row.reviewed_at=None;row.summary="正在识别体检报告"
        ReportIndicator.query.filter_by(report_id=row.id,user_id=user_id).delete();db.session.commit()
        return {"report_id":row.id,"status":row.status,"progress":row.progress}

    @staticmethod
    def defaults():
        return [{"indicator_name":"空腹血糖","indicator_code":"GLU","value":"6.8","unit":"mmol/L","reference_range":"3.9-6.1","status":"high","result_status":"high","risk_level":"medium"},{"indicator_name":"总胆固醇","indicator_code":"TC","value":"5.9","unit":"mmol/L","reference_range":"<5.2","status":"high","result_status":"high","risk_level":"medium"}]

    @classmethod
    def progress(cls,report_id,user_id=1):
        row=cls.get(report_id,user_id)
        if not row:return None
        if row.status in ("recognizing","extracting"):
            row.progress=min(100,(row.progress or 0)+35)
            if row.progress<70:row.status="recognizing";message="正在进行 OCR 识别"
            elif row.progress<100:row.status="extracting";message="正在提取关键指标"
            else:row.status="review_pending";row.confidence=.92;row.summary="空腹血糖、总胆固醇偏高";cls.replace_indicators(row.id,cls.defaults(),user_id,commit=False);message="识别完成，等待管理员复核"
            db.session.commit()
        else:message="等待开始识别" if row.status=="uploaded" else "处理完成"
        return {"report_id":row.id,"status":row.status,"progress":row.progress,"message":message}

    @classmethod
    def history(cls,page,page_size,user_id=1):
        q=MedicalReport.query.filter_by(user_id=user_id);total=q.count();rows=q.order_by(MedicalReport.uploaded_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"items":[{"id":r.id,"file_name":r.file_name,"report_date":r.report_date.isoformat(),"status":r.status,"summary":r.summary or ""} for r in rows],"page":page,"page_size":page_size,"total":total}

    @staticmethod
    def indicators(report_id,user_id=1):
        rows=ReportIndicator.query.filter_by(report_id=report_id,user_id=user_id).order_by(ReportIndicator.id).all()
        return [{"id":r.id,"report_id":r.report_id,"user_id":r.user_id,"indicator_name":r.indicator_name,"indicator_code":r.indicator_code,"value":r.value,"unit":r.unit,"reference_range":r.reference_range,"status":r.result_status,"result_status":r.result_status,"risk_level":r.risk_level,"created_at":r.created_at.isoformat()} for r in rows]

    @classmethod
    def replace_indicators(cls,report_id,items,user_id=1,commit=True):
        ReportIndicator.query.filter_by(report_id=report_id,user_id=user_id).delete()
        now=_now()
        for item in items:db.session.add(ReportIndicator(report_id=report_id,user_id=user_id,indicator_name=item["indicator_name"],indicator_code=item.get("indicator_code"),value=str(item["value"]),unit=item.get("unit"),reference_range=item.get("reference_range"),result_status=item.get("result_status",item.get("status","normal")),risk_level=item.get("risk_level","low"),created_at=now))
        if commit:db.session.commit()

    @classmethod
    def update_indicators(cls,report_id,items,user_id=1):
        row=cls.get(report_id,user_id)
        if not row:return None
        cls.replace_indicators(report_id,items,user_id,commit=False);row.status="review_pending";row.summary="指标已人工纠正，等待确认";db.session.commit();return cls.indicators(report_id,user_id)

    @classmethod
    def confirm(cls,report_id,note="",user_id=1):
        row=cls.get(report_id,user_id)
        if not row:return None
        if ReportIndicator.query.filter_by(report_id=report_id,user_id=user_id).count()==0:return False
        row.status="completed";row.review_note=note;row.reviewed_at=_now();row.summary=note or row.summary or "报告指标已确认";db.session.commit();return cls.detail(row)

    @classmethod
    def delete(cls,report_id,user_id=1):
        row=cls.get(report_id,user_id)
        if not row:return None
        result={"file_url":row.file_url};ReportIndicator.query.filter_by(report_id=report_id,user_id=user_id).delete();db.session.delete(row);db.session.commit();return result

    @classmethod
    def review(cls,report_id,payload):
        row=db.session.get(MedicalReport,report_id)
        if not row:return None
        row.status=payload.get("status","completed");row.review_note=payload.get("review_note","");row.reviewed_at=_now()
        if payload.get("indicators"):cls.replace_indicators(row.id,payload["indicators"],row.user_id,commit=False)
        db.session.commit();return {"report_id":row.id,"status":row.status,"reviewed_at":row.reviewed_at.isoformat()}

    @classmethod
    def batch_review(cls,ids,status,note=""):
        done=[item for item in ids if cls.review(item,{"status":status,"review_note":note})]
        return {"requested_count":len(ids),"processed_count":len(done),"processed_ids":done,"missing_ids":[x for x in ids if x not in done]}

    @staticmethod
    def admin_list(page,page_size,status=None):
        q=db.session.query(MedicalReport,User).join(User,User.id==MedicalReport.user_id)
        if status:q=q.filter(MedicalReport.status==status)
        total=q.count();rows=q.order_by(MedicalReport.uploaded_at.desc()).offset((page-1)*page_size).limit(page_size).all()
        return {"items":[{"id":r.id,"user_name":u.username,"file_name":r.file_name,"status":r.status,"confidence":_number(r.confidence),"summary":r.summary or "","created_at":r.uploaded_at.isoformat()} for r,u in rows],"page":page,"page_size":page_size,"total":total}

    @staticmethod
    def pending_count():return MedicalReport.query.filter_by(status="review_pending").count()


def bootstrap_report_data(store):
    for s in store.reports.values():db.session.merge(MedicalReport(id=s["id"],user_id=s.get("user_id",1),file_name=s["file_name"],file_type=s["file_type"],file_url=s.get("file_url"),source=s.get("source",s["file_type"]),report_date=_date(s.get("report_date") or date.today()),status=s.get("status","uploaded"),confidence=s.get("confidence"),progress=s.get("progress",0),summary=s.get("summary",""),review_note=s.get("review_note",""),uploaded_at=_datetime(s.get("uploaded_at") or s.get("created_at")) or _now(),reviewed_at=_datetime(s.get("reviewed_at"))))
    db.session.flush()
    for report_id,items in store.indicators_by_report_id.items():
        for s in items:db.session.merge(ReportIndicator(id=s["id"],report_id=int(report_id),user_id=s.get("user_id",1),indicator_name=s["indicator_name"],indicator_code=s.get("indicator_code"),value=str(s["value"]),unit=s.get("unit"),reference_range=s.get("reference_range"),result_status=s.get("result_status",s.get("status","normal")),risk_level=s.get("risk_level","low"),created_at=_datetime(s.get("created_at")) or _now()))
    db.session.commit()
