from app.models import Prompt, AssetGroup, AssetImage, Provider, GenTask, TaskImage

def test_prompt_roundtrip(db):
    p = Prompt(name="街拍白裙", content="A photo of ...", tags="街拍")
    db.add(p); db.commit()
    assert p.id is not None and p.updated_at is not None

def test_group_name_unique_per_library(db):
    db.add(AssetGroup(library=1, name="模特A"))
    db.add(AssetGroup(library=1, name="模特A"))
    try:
        db.commit(); assert False, "应触发同库组名唯一约束"
    except Exception: db.rollback()

def test_cascade_delete_images(db):
    g = AssetGroup(library=3, name="白袜")
    g.images.append(AssetImage(library=3, original_name="a.png", file_path="socks/1/a.png"))
    db.add(g); db.commit()
    gid = g.id
    db.delete(g); db.commit()
    assert db.query(AssetImage).filter_by(group_id=gid).count() == 0
