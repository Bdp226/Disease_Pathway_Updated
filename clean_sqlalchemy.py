from database import SessionLocal, PainPoint, PainPointView
db = SessionLocal()

pp133 = db.query(PainPoint).filter(PainPoint.id == 133).first()
if pp133:
    print("Found ID 133, deleting...")
    db.query(PainPointView).filter(PainPointView.pain_point_id == 133).delete()
    db.delete(pp133)
    db.commit()
    print("Deleted.")
else:
    print("ID 133 not found in SQLAlchemy either.")

# Let's also look for exact 'test'
fake_pps = db.query(PainPoint).filter(PainPoint.description == 'test').all()
for p in fake_pps:
    print(f"Found fake {p.id}")
    db.query(PainPointView).filter(PainPointView.pain_point_id == p.id).delete()
    db.delete(p)
db.commit()
