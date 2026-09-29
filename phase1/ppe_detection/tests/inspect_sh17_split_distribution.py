from pathlib import Path
from collections import Counter


ROOT = Path(
    "phase1/ppe_detection/data/raw/SH17"
)

LABEL_DIR = (
    ROOT
    / "labels"
)


SH17_CLASS_NAMES = {
    0: "person",
    1: "ear",
    2: "ear-mufs",
    3: "face",
    4: "face-guard",
    5: "face-mask-medical",
    6: "foot",
    7: "tools",
    8: "glasses",
    9: "gloves",
    10: "helmet",
    11: "hands",
    12: "head",
    13: "medical-suit",
    14: "shoes",
    15: "safety-suit",
    16: "safety-vest",
}


def read_manifest(
    path,
):

    return [
        line.strip()
        for line
        in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def inspect_manifest(
    manifest,
):

    image_class_counts = Counter()

    object_class_counts = Counter()


    for image_name in manifest:

        label_path = (
            LABEL_DIR
            / f"{Path(image_name).stem}.txt"
        )


        if not label_path.exists():

            raise FileNotFoundError(
                f"Missing label: {label_path}"
            )


        image_classes = set()


        for line in label_path.read_text(
            encoding="utf-8"
        ).splitlines():

            line = line.strip()


            if not line:

                continue


            class_id = int(
                line.split()[0]
            )


            object_class_counts[
                class_id
            ] += 1


            image_classes.add(
                class_id
            )


        for class_id in image_classes:

            image_class_counts[
                class_id
            ] += 1


    return (
        image_class_counts,
        object_class_counts,
    )


train_manifest = read_manifest(
    ROOT
    / "train_files.txt"
)

val_manifest = read_manifest(
    ROOT
    / "val_files.txt"
)


for split_name, manifest in [
    (
        "OFFICIAL TRAIN",
        train_manifest,
    ),
    (
        "OFFICIAL VALIDATION",
        val_manifest,
    ),
]:

    image_counts, object_counts = (
        inspect_manifest(
            manifest
        )
    )


    print(
        "\n============================================"
    )

    print(
        split_name
    )

    print(
        "============================================"
    )


    print(
        "Images:",
        len(
            manifest
        ),
    )


    print()


    print(
        f"{'ID':<4}"
        f"{'Class':<22}"
        f"{'Images':>10}"
        f"{'Objects':>12}"
    )


    print(
        "-" * 48
    )


    for class_id, class_name in (
        SH17_CLASS_NAMES.items()
    ):

        print(
            f"{class_id:<4}"
            f"{class_name:<22}"
            f"{image_counts[class_id]:>10}"
            f"{object_counts[class_id]:>12}"
        )