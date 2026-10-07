"""
DC-Guardian Evidence
Controlled Face Dataset Contract Test

Validates the controlled face-identification dataset before
enrollment, threshold selection, or final evaluation.
"""

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import re


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

DATASET_ROOT = (
    PROJECT_ROOT
    / "evidence"
    / "face_recognition"
    / "data"
    / "controlled_faces"
)


# ============================================================
# Frozen dataset contract
# ============================================================

EXPECTED_IDENTITIES = {
    "enrollment": {
        "P001",
        "P002",
        "P003",
        "P004",
        "P005",
    },

    "validation_known": {
        "P001",
        "P002",
        "P003",
        "P004",
        "P005",
    },

    "validation_unknown": {
        "VU001",
        "VU002",
        "VU003",
    },

    "test_known": {
        "P001",
        "P002",
        "P003",
        "P004",
        "P005",
    },

    "test_unknown": {
        "U001",
        "U002",
        "U003",
        "U004",
        "U005",
    },
}

EXPECTED_IMAGE_COUNTS = {
    "enrollment": 18,
    "validation_known": 7,
    "validation_unknown": 6,
    "test_known": 6,
    "test_unknown": 9,
}


EXPECTED_TOTAL_IMAGES = 46


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
}


FILENAME_PATTERNS = {
    "enrollment":
        re.compile(
            r"^P\d{3}_enroll_\d{2}\.(jpg|jpeg|png)$",
            re.IGNORECASE,
        ),

    "validation_known":
        re.compile(
            r"^P\d{3}_val_\d{2}\.(jpg|jpeg|png)$",
            re.IGNORECASE,
        ),

    "validation_unknown":
        re.compile(
            r"^VU\d{3}_val_\d{2}\.(jpg|jpeg|png)$",
            re.IGNORECASE,
        ),

    "test_known":
        re.compile(
            r"^P\d{3}_test_\d{2}\.(jpg|jpeg|png)$",
            re.IGNORECASE,
        ),

    "test_unknown":
        re.compile(
            r"^U\d{3}_test_\d{2}\.(jpg|jpeg|png)$",
            re.IGNORECASE,
        ),
}


# ============================================================
# Helpers
# ============================================================

def get_identity_directories(
    split_path,
):

    return {
        path.name
        for path
        in split_path.iterdir()
        if path.is_dir()
    }


def get_images(
    split_path,
):

    return sorted(
        path
        for path
        in split_path.rglob("*")
        if (
            path.is_file()
            and
            path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )
    )


def file_hash(
    path,
):

    digest = sha256()

    with path.open(
        "rb"
    ) as file:

        while True:

            block = file.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


# ============================================================
# Test
# ============================================================

print(
    "\n============================================"
)

print(
    "DC-GUARDIAN CONTROLLED FACE DATASET TEST"
)

print(
    "============================================"
)


# ============================================================
# Dataset root
# ============================================================

if not DATASET_ROOT.exists():

    raise AssertionError(
        "Controlled face dataset not found:\n"
        f"{DATASET_ROOT}"
    )


print(
    "PASS: Controlled dataset root found."
)


# ============================================================
# Required splits
# ============================================================

for split in EXPECTED_IDENTITIES:

    split_path = (
        DATASET_ROOT
        / split
    )

    if not split_path.is_dir():

        raise AssertionError(
            f"Required split missing: {split}"
        )


print(
    "PASS: Required dataset splits exist."
)


# ============================================================
# Identity contract
# ============================================================

for split, expected in (
    EXPECTED_IDENTITIES.items()
):

    split_path = (
        DATASET_ROOT
        / split
    )

    actual = (
        get_identity_directories(
            split_path
        )
    )

    if actual != expected:

        raise AssertionError(
            f"{split} identity mismatch.\n"
            f"Expected: {sorted(expected)}\n"
            f"Actual:   {sorted(actual)}"
        )


print(
    "PASS: Enrollment identities = P001-P005."
)

print(
    "PASS: Validation-known identities = P001-P005."
)

print(
    "PASS: Validation-unknown identities = VU001-VU003."
)

print(
    "PASS: Known-test identities = P001-P005."
)

print(
    "PASS: Unknown-test identities = U001-U005."
)

# ============================================================
# Identity leakage
# ============================================================

enrolled = EXPECTED_IDENTITIES[
    "enrollment"
]

validation_unknown = EXPECTED_IDENTITIES[
    "validation_unknown"
]

test_unknown = EXPECTED_IDENTITIES[
    "test_unknown"
]


assert enrolled.isdisjoint(
    validation_unknown
)

assert enrolled.isdisjoint(
    test_unknown
)

assert validation_unknown.isdisjoint(
    test_unknown
)


print(
    "PASS: Validation-unknown identities "
    "are not enrolled."
)

print(
    "PASS: Final-test unknown identities "
    "are not enrolled."
)

print(
    "PASS: Validation-unknown and final-test "
    "unknown identities are independent."
)


# ============================================================
# Images and counts
# ============================================================

all_images = []

split_counts = {}


for split, expected_count in (
    EXPECTED_IMAGE_COUNTS.items()
):

    split_path = (
        DATASET_ROOT
        / split
    )

    images = get_images(
        split_path
    )

    split_counts[
        split
    ] = len(
        images
    )

    all_images.extend(
        (
            split,
            image,
        )
        for image
        in images
    )


    if len(images) != expected_count:

        raise AssertionError(
            f"{split} image-count mismatch.\n"
            f"Expected: {expected_count}\n"
            f"Actual:   {len(images)}"
        )


print(
    "PASS: Expected split image counts preserved."
)


if (
    len(all_images)
    != EXPECTED_TOTAL_IMAGES
):

    raise AssertionError(
        "Total image-count mismatch.\n"
        f"Expected: {EXPECTED_TOTAL_IMAGES}\n"
        f"Actual:   {len(all_images)}"
    )


print(
    "PASS: Total image count = "
    f"{EXPECTED_TOTAL_IMAGES}."
)


# ============================================================
# Every identity has at least one image
# ============================================================

for split in EXPECTED_IDENTITIES:

    split_path = (
        DATASET_ROOT
        / split
    )


    for identity in (
        EXPECTED_IDENTITIES[
            split
        ]
    ):

        identity_path = (
            split_path
            / identity
        )

        images = get_images(
            identity_path
        )


        if not images:

            raise AssertionError(
                "Identity contains no images: "
                f"{split}/{identity}"
            )




print(
    "PASS: Every identity contains images."
)


# ============================================================
# Reject unsupported files inside identity folders
# ============================================================

for split in EXPECTED_IDENTITIES:

    split_path = (
        DATASET_ROOT
        / split
    )


    for identity in (
        EXPECTED_IDENTITIES[
            split
        ]
    ):

        identity_path = (
            split_path
            / identity
        )


        for path in (
            identity_path.iterdir()
        ):

            if (
                path.is_file()
                and
                path.suffix.lower()
                not in SUPPORTED_EXTENSIONS
            ):

                raise AssertionError(
                    "Unsupported file found: "
                    f"{path}"
                )


print(
    "PASS: Supported image extensions only."
)


# ============================================================
# Filename contract
# ============================================================

for split, image in all_images:

    identity = (
        image.parent.name
    )


    pattern = (
        FILENAME_PATTERNS[
            split
        ]
    )


    if not pattern.match(
        image.name
    ):

        raise AssertionError(
            "Filename does not follow "
            "DC-Guardian naming contract:\n"
            f"{image}"
        )


    if not image.name.upper().startswith(
        identity.upper()
    ):

        raise AssertionError(
            "Filename identity does not "
            "match parent directory:\n"
            f"{image}"
        )


print(
    "PASS: Project-only filename "
    "convention preserved."
)


# ============================================================
# Exact duplicate detection
#
# Important:
# filenames are insufficient because the same image could have
# been copied and renamed into another split.
# ============================================================

hash_locations = defaultdict(
    list
)


for split, image in all_images:

    digest = file_hash(
        image
    )

    hash_locations[
        digest
    ].append(
        (
            split,
            image,
        )
    )


duplicates = {
    digest:
        locations

    for digest, locations
    in hash_locations.items()

    if len(
        locations
    ) > 1
}


if duplicates:

    lines = [
        "Duplicate image content detected:"
    ]


    for digest, locations in (
        duplicates.items()
    ):

        lines.append(
            f"\nSHA-256: {digest}"
        )


        for split, path in locations:

            lines.append(
                f"  {split}: {path}"
            )


    raise AssertionError(
        "\n".join(
            lines
        )
    )


print(
    "PASS: No exact duplicate images "
    "across dataset splits."
)


# ============================================================
# Final summary
# ============================================================

print(
    "\n============================================"
)

print(
    "CONTROLLED FACE DATASET SUMMARY"
)

print(
    "============================================"
)


print(
    "Enrolled identities: 5"
)

print(
    "Unknown identities:  5"
)
print(
    "Enrollment images:       ",
    split_counts[
        "enrollment"
    ],
)

print(
    "Validation-known images: ",
    split_counts[
        "validation_known"
    ],
)

print(
    "Validation-unknown images:",
    split_counts[
        "validation_unknown"
    ],
)

print(
    "Known-test images:       ",
    split_counts[
        "test_known"
    ],
)

print(
    "Unknown-test images:     ",
    split_counts[
        "test_unknown"
    ],
)

print(
    "Total images:            ",
    len(
        all_images
    ),
)

print(
    "\n============================================"
)

print(
    "CONTROLLED FACE DATASET CONTRACT PASSED"
)

print(
    "============================================"
)
