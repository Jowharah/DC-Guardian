from presentation.backend.app.physical_person_association import associate

def evidence():
    p={"detections":[{"class_name":"person","bbox_xyxy":[0,0,100,200]},
                     {"class_name":"person","bbox_xyxy":[120,0,220,200]}],
       "people":[{"status":"COMPLIANT"},{"status":"NON_COMPLIANT"}]}
    f={"recognition_status":"RECOGNIZED","person_id":"P005",
       "facial_area":{"x":20,"y":20,"w":40,"h":40}}
    return p,f

def test_unique_same_image_match_is_only_candidate():
    p,f=evidence()
    result=associate(p,f,True)
    assert result["status"]=="MATCH_CANDIDATE"
    assert result["person_index"]==0
    assert result["ppe_status"]=="COMPLIANT"
    assert result["identity_link_established"] is False

def test_different_images_cannot_use_pixel_geometry():
    p,f=evidence()
    assert associate(p,f,False)["status"]=="NOT_EVALUATED"

def test_missing_face_geometry_abstains():
    p,f=evidence();f["facial_area"]=None
    assert associate(p,f,True)["status"]=="NOT_EVALUATED"

def test_overlap_without_person_abstains():
    p,f=evidence();f["facial_area"]={"x":300,"y":20,"w":40,"h":40}
    assert associate(p,f,True)["status"]=="NO_MATCH"

def test_ambiguous_overlapping_people_abstains():
    p,f=evidence();p["detections"][1]["bbox_xyxy"]=[0,0,100,200]
    assert associate(p,f,True)["status"]=="AMBIGUOUS"
