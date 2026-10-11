from pathlib import Path
from collections import defaultdict, Counter
import xml.etree.ElementTree as ET


ROOT = Path(
    "evidence/ppe_detection/data/raw/SH17"
)

YOLO_DIR = ROOT / "labels"
VOC_DIR = ROOT / "voc_labels"


mapping_votes = defaultdict(
    Counter
)


for yolo_path in sorted(
    YOLO_DIR.glob("*.txt")
):

    voc_path = (
        VOC_DIR
        / f"{yolo_path.stem}.xml"
    )

    if not voc_path.exists():
        continue


    # --------------------------------------------
    # YOLO objects
    # --------------------------------------------

    yolo_rows = []

    for line in yolo_path.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) != 5:
            continue

        yolo_rows.append(
            int(parts[0])
        )


    # --------------------------------------------
    # VOC objects
    # --------------------------------------------

    tree = ET.parse(
        voc_path
    )

    root = tree.getroot()

    voc_names = [
        obj.findtext("name")
        for obj in root.findall("object")
    ]


    # --------------------------------------------
    # SH17 YOLO/VOC annotations are expected to
    # describe the same objects in corresponding
    # order. Only use files where counts match.
    # --------------------------------------------

    if (
        len(yolo_rows)
        != len(voc_names)
    ):
        continue


    for class_id, class_name in zip(
        yolo_rows,
        voc_names,
    ):

        mapping_votes[
            class_id
        ][
            class_name
        ] += 1


print(
    "\n============================================"
)
print(
    "SH17 YOLO -> VOC CLASS MAPPING INSPECTION"
)
print(
    "============================================"
)


for class_id in sorted(
    mapping_votes
):

    votes = mapping_votes[
        class_id
    ]

    best_name, best_count = (
        votes.most_common(
            1
        )[0]
    )

    total = sum(
        votes.values()
    )

    print(
        f"{class_id:2d} -> "
        f"{best_name:<20} "
        f"{best_count}/{total}"
    )


    if len(votes) > 1:

        print(
            "     alternatives:",
            dict(
                votes
            ),
        )
