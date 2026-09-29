"""
DC-Guardian Phase 1
SH17 PPE Dataset Preparation

Purpose:
- Preserve the official SH17 training split unchanged.
- Partition the official SH17 validation population into:
    * development validation
    * locked final test
- Preserve representation of rare classes where possible.
- Generate immutable project manifests.
- Generate Ultralytics dataset.yaml.

IMPORTANT:
The locked final-test manifest must not be used during
training, model selection, threshold selection, or PPE-policy
development.
"""

from pathlib import Path
from collections import Counter
import random
import yaml


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

PPE_ROOT = (
    PROJECT_ROOT
    / "phase1"
    / "ppe_detection"
)

RAW_ROOT = (
    PPE_ROOT
    / "data"
    / "raw"
    / "SH17"
)

PROCESSED_ROOT = (
    PPE_ROOT
    / "data"
    / "processed"
    / "sh17_yolo"
)

IMAGE_DIR = RAW_ROOT / "images"
LABEL_DIR = RAW_ROOT / "labels"

OFFICIAL_TRAIN = (
    RAW_ROOT
    / "train_files.txt"
)

OFFICIAL_VAL = (
    RAW_ROOT
    / "val_files.txt"
)


SEED = 42

EXPECTED_TOTAL = 8099
EXPECTED_TRAIN = 6479
EXPECTED_OFFICIAL_VAL = 1620

VALIDATION_TARGET = 810
TEST_TARGET = 810


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


# ============================================================
# Helpers
# ============================================================

def read_manifest(path):

    names = [
        line.strip()
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    return names


def label_path_for(image_name):

    return (
        LABEL_DIR
        / f"{Path(image_name).stem}.txt"
    )


def image_classes(image_name):
    """
    Return the set of SH17 class IDs present in one image.
    """

    label_path = label_path_for(
        image_name
    )

    if not label_path.exists():

        raise FileNotFoundError(
            f"Missing YOLO label: {label_path}"
        )


    classes = set()


    for line in label_path.read_text(
        encoding="utf-8"
    ).splitlines():

        line = line.strip()

        if not line:
            continue


        parts = line.split()


        if len(parts) != 5:

            raise ValueError(
                f"Invalid YOLO annotation in {label_path}: "
                f"{line}"
            )


        class_id = int(
            parts[0]
        )


        if class_id not in SH17_CLASS_NAMES:

            raise ValueError(
                f"Unknown SH17 class ID {class_id} "
                f"in {label_path}"
            )


        classes.add(
            class_id
        )


    return classes


def class_image_counts(names):

    counts = Counter()


    for image_name in names:

        for class_id in image_classes(
            image_name
        ):

            counts[
                class_id
            ] += 1


    return counts


def write_manifest(
    path,
    names,
):

    path.write_text(
        "\n".join(
            names
        )
        + "\n",
        encoding="utf-8",
    )


# ============================================================
# Multi-label balanced partition
# ============================================================

def balanced_partition(
    names,
):
    """
    Deterministically split the official validation population
    into two equal populations while attempting to preserve
    rare-class representation.

    This is a project-controlled split, not an official SH17
    test split.
    """

    rng = random.Random(
        SEED
    )


    names = list(
        names
    )


    class_sets = {
        name:
            image_classes(
                name
            )
        for name in names
    }


    total_counts = class_image_counts(
        names
    )


    # Desired validation representation is approximately half
    # of every class's official-validation image population.
    targets = {
        class_id:
            total_counts[
                class_id
            ]
            / 2.0

        for class_id
        in SH17_CLASS_NAMES
    }


    # Rare-class images receive higher priority.
    def rarity_score(
        image_name,
    ):

        classes = class_sets[
            image_name
        ]


        if not classes:

            return 0.0


        return sum(
            1.0
            / max(
                total_counts[
                    class_id
                ],
                1,
            )

            for class_id
            in classes
        )


    # Shuffle first so equal-score cases are deterministic
    # but not dependent on filename ordering.
    rng.shuffle(
        names
    )


    names.sort(
        key=rarity_score,
        reverse=True,
    )


    validation = []

    test = []

    validation_counts = Counter()

    test_counts = Counter()


    for image_name in names:

        classes = class_sets[
            image_name
        ]


        if len(validation) >= VALIDATION_TARGET:

            test.append(
                image_name
            )

            for class_id in classes:
                test_counts[
                    class_id
                ] += 1

            continue


        if len(test) >= TEST_TARGET:

            validation.append(
                image_name
            )

            for class_id in classes:
                validation_counts[
                    class_id
                ] += 1

            continue


        # Calculate how much each side currently needs the
        # classes contained in this image.
        validation_need = sum(
            max(
                targets[
                    class_id
                ]
                - validation_counts[
                    class_id
                ],
                0.0,
            )

            for class_id
            in classes
        )


        test_need = sum(
            max(
                targets[
                    class_id
                ]
                - test_counts[
                    class_id
                ],
                0.0,
            )

            for class_id
            in classes
        )


        if validation_need > test_need:

            destination = (
                validation
            )

            destination_counts = (
                validation_counts
            )


        elif test_need > validation_need:

            destination = (
                test
            )

            destination_counts = (
                test_counts
            )


        else:

            # Keep population sizes balanced when class need
            # is tied.
            if (
                len(validation)
                <= len(test)
            ):

                destination = (
                    validation
                )

                destination_counts = (
                    validation_counts
                )

            else:

                destination = (
                    test
                )

                destination_counts = (
                    test_counts
                )


        destination.append(
            image_name
        )


        for class_id in classes:

            destination_counts[
                class_id
            ] += 1


    if len(validation) != VALIDATION_TARGET:

        raise AssertionError(
            "Validation population mismatch: "
            f"{len(validation)}"
        )


    if len(test) != TEST_TARGET:

        raise AssertionError(
            "Test population mismatch: "
            f"{len(test)}"
        )


    return (
        sorted(
            validation
        ),
        sorted(
            test
        ),
    )


# ============================================================
# Main
# ============================================================

def main():

    print(
        "\n============================================"
    )

    print(
        "DC-GUARDIAN SH17 DATASET PREPARATION"
    )

    print(
        "============================================"
    )


    # --------------------------------------------------------
    # Raw contract
    # --------------------------------------------------------

    required_paths = [
        RAW_ROOT,
        IMAGE_DIR,
        LABEL_DIR,
        OFFICIAL_TRAIN,
        OFFICIAL_VAL,
    ]


    for path in required_paths:

        if not path.exists():

            raise FileNotFoundError(
                f"Required SH17 path missing: {path}"
            )


    train_names = read_manifest(
        OFFICIAL_TRAIN
    )

    official_val_names = read_manifest(
        OFFICIAL_VAL
    )


    if len(train_names) != EXPECTED_TRAIN:

        raise AssertionError(
            "Official training count mismatch."
        )


    if (
        len(official_val_names)
        != EXPECTED_OFFICIAL_VAL
    ):

        raise AssertionError(
            "Official validation count mismatch."
        )


    if (
        len(train_names)
        + len(official_val_names)
        != EXPECTED_TOTAL
    ):

        raise AssertionError(
            "SH17 total manifest count mismatch."
        )


    overlap = (
        set(
            train_names
        )
        &
        set(
            official_val_names
        )
    )


    if overlap:

        raise AssertionError(
            "Official SH17 train/validation "
            "populations overlap."
        )


    print(
        "PASS: Official SH17 populations verified."
    )


    # --------------------------------------------------------
    # Image / label existence
    # --------------------------------------------------------

    for image_name in (
        train_names
        + official_val_names
    ):

        image_path = (
            IMAGE_DIR
            / image_name
        )


        if not image_path.exists():

            raise FileNotFoundError(
                f"Missing SH17 image: {image_path}"
            )


        label_path = label_path_for(
            image_name
        )


        if not label_path.exists():

            raise FileNotFoundError(
                f"Missing SH17 label: {label_path}"
            )


    print(
        "PASS: Every manifest entry has image and label."
    )


    # --------------------------------------------------------
    # Controlled validation/test partition
    # --------------------------------------------------------

    validation_names, test_names = (
        balanced_partition(
            official_val_names
        )
    )


    if (
        set(
            validation_names
        )
        &
        set(
            test_names
        )
    ):

        raise AssertionError(
            "Validation/test populations overlap."
        )


    if (
        set(
            validation_names
        )
        |
        set(
            test_names
        )
        != set(
            official_val_names
        )
    ):

        raise AssertionError(
            "Validation/test partition does not preserve "
            "the complete official validation population."
        )


    print(
        "PASS: Controlled validation/test "
        "partition created."
    )


    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    PROCESSED_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


    train_manifest = (
        PROCESSED_ROOT
        / "train_files.txt"
    )

    validation_manifest = (
        PROCESSED_ROOT
        / "validation_files.txt"
    )

    test_manifest = (
        PROCESSED_ROOT
        / "test_files.txt"
    )


    write_manifest(
        train_manifest,
        train_names,
    )

    write_manifest(
        validation_manifest,
        validation_names,
    )

    write_manifest(
        test_manifest,
        test_names,
    )


    # --------------------------------------------------------
    # Ultralytics manifests
    #
    # Ultralytics accepts text files containing absolute image
    # paths as train/val definitions.
    # --------------------------------------------------------

    train_image_list = (
        PROCESSED_ROOT
        / "train_images.txt"
    )

    validation_image_list = (
        PROCESSED_ROOT
        / "validation_images.txt"
    )


    train_image_list.write_text(
        "\n".join(
            str(
                (
                    IMAGE_DIR
                    / image_name
                ).resolve()
            )

            for image_name
            in train_names
        )
        + "\n",
        encoding="utf-8",
    )


    validation_image_list.write_text(
        "\n".join(
            str(
                (
                    IMAGE_DIR
                    / image_name
                ).resolve()
            )

            for image_name
            in validation_names
        )
        + "\n",
        encoding="utf-8",
    )


    # IMPORTANT:
    # dataset.yaml intentionally contains NO test entry.
    #
    # This prevents ordinary Ultralytics training/validation
    # calls from accidentally touching the locked test set.

    dataset_config = {
        "train":
            str(
                train_image_list.resolve()
            ),

        "val":
            str(
                validation_image_list.resolve()
            ),

        "nc":
            len(
                SH17_CLASS_NAMES
            ),

        "names": [
            SH17_CLASS_NAMES[
                class_id
            ]

            for class_id
            in range(
                len(
                    SH17_CLASS_NAMES
                )
            )
        ],
    }


    dataset_yaml = (
        PROCESSED_ROOT
        / "dataset.yaml"
    )


    with dataset_yaml.open(
        "w",
        encoding="utf-8",
    ) as file:

        yaml.safe_dump(
            dataset_config,
            file,
            sort_keys=False,
        )


    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    val_counts = class_image_counts(
        validation_names
    )

    test_counts = class_image_counts(
        test_names
    )


    print()
    print(
        "============================================"
    )

    print(
        "PROJECT PPE SPLIT SUMMARY"
    )

    print(
        "============================================"
    )


    print(
        f"Train:      {len(train_names)}"
    )

    print(
        f"Validation: {len(validation_names)}"
    )

    print(
        f"Locked test:{len(test_names):>5}"
    )


    print()
    print(
        f"{'ID':<4}"
        f"{'Class':<22}"
        f"{'Validation':>12}"
        f"{'Test':>10}"
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
            f"{val_counts[class_id]:>12}"
            f"{test_counts[class_id]:>10}"
        )


    print()
    print(
        "Saved:",
        train_manifest,
    )

    print(
        "Saved:",
        validation_manifest,
    )

    print(
        "Saved:",
        test_manifest,
    )

    print(
        "Saved:",
        dataset_yaml,
    )


    print()
    print(
        "IMPORTANT:"
    )

    print(
        "The locked test manifest is NOT referenced "
        "by dataset.yaml."
    )


    print(
        "\n============================================"
    )

    print(
        "SH17 DATASET PREPARATION PASSED"
    )

    print(
        "============================================"
    )


if __name__ == "__main__":

    main()