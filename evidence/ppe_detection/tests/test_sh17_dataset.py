"""
DC-Guardian Phase 1
SH17 PPE Dataset Contract Test
"""

from pathlib import Path
from collections import Counter
import hashlib
import yaml


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

PPE_ROOT = PROJECT_ROOT / "evidence" / "ppe_detection"

RAW_ROOT = (
    PPE_ROOT / "data" / "raw" / "SH17"
)

PROCESSED_ROOT = (
    PPE_ROOT / "data" / "processed" / "sh17_yolo"
)

IMAGE_DIR = RAW_ROOT / "images"
LABEL_DIR = RAW_ROOT / "labels"

TRAIN_MANIFEST = PROCESSED_ROOT / "train_files.txt"
VAL_MANIFEST = PROCESSED_ROOT / "validation_files.txt"
TEST_MANIFEST = PROCESSED_ROOT / "test_files.txt"
DATASET_YAML = PROCESSED_ROOT / "dataset.yaml"


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


EXPECTED_TRAIN = 6479
EXPECTED_VAL = 810
EXPECTED_TEST = 810
EXPECTED_TOTAL = 8099


def read_manifest(path):

    return [
        line.strip()
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]


def image_hash(path):

    digest = hashlib.sha256()

    with path.open("rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_annotation(label_path):

    classes = []

    for line_number, line in enumerate(
        label_path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):

        line = line.strip()

        if not line:
            continue

        fields = line.split()

        if len(fields) != 5:

            raise AssertionError(
                f"{label_path}:{line_number} "
                "must contain 5 YOLO fields."
            )

        class_id = int(fields[0])

        if class_id not in SH17_CLASS_NAMES:

            raise AssertionError(
                f"Invalid class ID {class_id} "
                f"in {label_path}"
            )

        values = [
            float(value)
            for value in fields[1:]
        ]

        x, y, width, height = values

        if not all(
            0.0 <= value <= 1.0
            for value in values
        ):

            raise AssertionError(
                f"Non-normalized YOLO box in "
                f"{label_path}:{line_number}"
            )

        if width <= 0 or height <= 0:

            raise AssertionError(
                f"Zero-size box in "
                f"{label_path}:{line_number}"
            )

        classes.append(class_id)

    return classes


print(
    "\n============================================"
)
print(
    "DC-GUARDIAN SH17 PPE DATASET TEST"
)
print(
    "============================================"
)


# ============================================================
# Required artifacts
# ============================================================

for path in [
    RAW_ROOT,
    IMAGE_DIR,
    LABEL_DIR,
    TRAIN_MANIFEST,
    VAL_MANIFEST,
    TEST_MANIFEST,
    DATASET_YAML,
]:

    if not path.exists():

        raise AssertionError(
            f"Required PPE dataset artifact missing: {path}"
        )


print(
    "PASS: Required SH17 dataset artifacts exist."
)


# ============================================================
# Manifests
# ============================================================

train = read_manifest(
    TRAIN_MANIFEST
)

validation = read_manifest(
    VAL_MANIFEST
)

test = read_manifest(
    TEST_MANIFEST
)


assert len(train) == EXPECTED_TRAIN
assert len(validation) == EXPECTED_VAL
assert len(test) == EXPECTED_TEST


assert (
    len(train)
    + len(validation)
    + len(test)
    == EXPECTED_TOTAL
)


print(
    "PASS: Frozen split image counts preserved."
)


# ============================================================
# No filename overlap
# ============================================================

train_set = set(train)
val_set = set(validation)
test_set = set(test)


assert not (
    train_set & val_set
)

assert not (
    train_set & test_set
)

assert not (
    val_set & test_set
)


assert (
    train_set
    | val_set
    | test_set
) and len(
    train_set
    | val_set
    | test_set
) == EXPECTED_TOTAL


print(
    "PASS: Train/validation/test populations are disjoint."
)


# ============================================================
# Image + label integrity
# ============================================================

split_classes = {
    "train": Counter(),
    "validation": Counter(),
    "test": Counter(),
}


for split_name, manifest in [
    ("train", train),
    ("validation", validation),
    ("test", test),
]:

    for image_name in manifest:

        image_path = (
            IMAGE_DIR
            / image_name
        )

        label_path = (
            LABEL_DIR
            / f"{Path(image_name).stem}.txt"
        )


        if not image_path.exists():

            raise AssertionError(
                f"Missing image: {image_path}"
            )


        if not label_path.exists():

            raise AssertionError(
                f"Missing label: {label_path}"
            )


        class_ids = validate_annotation(
            label_path
        )


        for class_id in set(
            class_ids
        ):

            split_classes[
                split_name
            ][
                class_id
            ] += 1


print(
    "PASS: Every split image has a valid YOLO label."
)

print(
    "PASS: All YOLO coordinates are normalized."
)

print(
    "PASS: All class IDs lie within 0-16."
)


# ============================================================
# Every class represented
# ============================================================

for split_name in [
    "train",
    "validation",
    "test",
]:

    missing = [
        SH17_CLASS_NAMES[
            class_id
        ]

        for class_id in SH17_CLASS_NAMES

        if (
            split_classes[
                split_name
            ][
                class_id
            ]
            == 0
        )
    ]


    if missing:

        raise AssertionError(
            f"{split_name} missing classes: {missing}"
        )


print(
    "PASS: All 17 classes represented in every split."
)


# ============================================================
# dataset.yaml contract
# ============================================================

with DATASET_YAML.open(
    "r",
    encoding="utf-8",
) as file:

    config = yaml.safe_load(
        file
    )


assert config[
    "nc"
] == 17


assert config[
    "names"
] == [
    SH17_CLASS_NAMES[
        class_id
    ]
    for class_id in range(17)
]


if "test" in config:

    raise AssertionError(
        "Locked final-test population must not be "
        "referenced by dataset.yaml."
    )


yaml_text = DATASET_YAML.read_text(
    encoding="utf-8"
)


if "test_files.txt" in yaml_text:

    raise AssertionError(
        "Locked test manifest leaked into dataset.yaml."
    )


print(
    "PASS: SH17 17-class vocabulary frozen."
)

print(
    "PASS: Locked final test excluded from dataset.yaml."
)


# ============================================================
# Exact duplicate leakage
# ============================================================

hashes = {}


for split_name, manifest in [
    ("train", train),
    ("validation", validation),
    ("test", test),
]:

    hashes[
        split_name
    ] = {
        image_hash(
            IMAGE_DIR
            / image_name
        )
        for image_name in manifest
    }


for left, right in [
    ("train", "validation"),
    ("train", "test"),
    ("validation", "test"),
]:

    overlap = (
        hashes[left]
        &
        hashes[right]
    )


    if overlap:

        raise AssertionError(
            "Exact duplicate image leakage between "
            f"{left} and {right}: "
            f"{len(overlap)} image(s)."
        )


print(
    "PASS: No exact duplicate images across project splits."
)


# ============================================================
# Summary
# ============================================================

print(
    "\n============================================"
)
print(
    "SH17 PPE DATASET SUMMARY"
)
print(
    "============================================"
)

print(
    "Classes:     17"
)

print(
    f"Train:       {len(train)}"
)

print(
    f"Validation:  {len(validation)}"
)

print(
    f"Locked test: {len(test)}"
)

print(
    f"Total:       {EXPECTED_TOTAL}"
)


print(
    "\nClass vocabulary:"
)

for class_id, class_name in (
    SH17_CLASS_NAMES.items()
):

    print(
        f"  {class_id:2d}: {class_name}"
    )


print(
    "\n============================================"
)
print(
    "SH17 PPE DATASET CONTRACT PASSED"
)
print(
    "============================================"
)
