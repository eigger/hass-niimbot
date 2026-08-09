from enum import Enum
from typing import List, NotRequired, TypedDict, Union

class PrintGeneration(Enum):
    OLD_D11 = "OLD_D11"
    D110 = "D110"
    V4 = "V4"
    V5 = "V5"

class PrintDirection(Enum):
    TOP = "top"
    LEFT = "left"

class LabelType(Enum):
    WITH_GAPS = "WithGaps"
    BLACK = "Black"
    CONTINUOUS = "Continuous"
    TRANSPARENT = "Transparent"
    HEAT_SHRINK_TUBE = "HeatShrinkTube"
    BLACK_MARK_GAP = "BlackMarkGap"
    PVC_TAG = "PvcTag"
    PERFORATED = "Perforated"

class RfidClass(Enum):
    NONE = "none"
    LABEL = "label"
    RIBBON = "ribbon"
    LABEL_RIBBON = "label_ribbon"

class PrinterModel(Enum):
    UNKNOWN = "UNKNOWN"
    B3S_P = "B3S_P"
    T2S = "T2S"
    N1 = "N1"
    TP2M_H = "TP2M_H"
    B31 = "B31"
    B21_PRO = "B21_PRO"
    B2_PRO = "B2_PRO"
    B2 = "B2"
    B18S = "B18S"
    D11_H = "D11_H"
    B21_H = "B21_H"
    HI_D110 = "HI_D110"
    D110_M = "D110_M"
    M2_H = "M2_H"
    A20 = "A20"
    MP3K_W = "MP3K_W"
    A203 = "A203"
    MP3K = "MP3K"
    K3_W = "K3_W"
    K3 = "K3"
    BETTY = "BETTY"
    T8S = "T8S"
    DXX = "DXX"
    B21S = "B21S"
    B21_L2B = "B21_L2B"
    D11S = "D11S"
    A63 = "A63"
    FUST = "FUST"
    P1 = "P1"
    P18 = "P18"
    S6 = "S6"
    B21S_C2B = "B21S_C2B"
    P1S = "P1S"
    B1 = "B1"
    B1_PRO = "B1_PRO"
    A8 = "A8"
    B21_C2B = "B21_C2B"
    Z401 = "Z401"
    B16 = "B16"
    B32R = "B32R"
    B32 = "B32"
    D41 = "D41"
    S3 = "S3"
    JC_M90 = "JC_M90"
    JCB3S = "JCB3S"
    B203 = "B203"
    S1 = "S1"
    D61 = "D61"
    D110 = "D110"
    D11_PRO = "D11_PRO"
    B21 = "B21"
    D101 = "D101"
    HI_NB_D11 = "HI_NB_D11"
    A8_P = "A8_P"
    S6_P = "S6_P"
    T6 = "T6"
    B50W = "B50W"
    T7 = "T7"
    T8 = "T8"
    B3S = "B3S"
    B3 = "B3"
    B18 = "B18"
    D11 = "D11"
    B11 = "B11"
    B50 = "B50"
    ET10 = "ET10"
    H1 = "H1"
    B1_SE = "B1_SE"
    H1S = "H1S"
    EP2M_H = "EP2M_H"
    K3_ITD = "K3_ITD"
    C1 = "C1"
    EP1C = "EP1C"
    K2 = "K2"
    M3 = "M3"
    EP3M = "EP3M"
    B4 = "B4"
    B4_PRO = "B4_PRO"
    K4 = "K4"
    A1_PRO = "A1_PRO"

class PrinterModelMeta(TypedDict):
    model: PrinterModel
    id: List[int]
    dpi: int
    printDirection: PrintDirection
    printheadPixels: int
    paperTypes: List[LabelType]
    generation: PrintGeneration
    rfid: NotRequired[RfidClass]
    densityMin: NotRequired[int]
    densityMax: NotRequired[int]
    densityDefault: NotRequired[int]
    printheadPixelsEstimated: NotRequired[bool]

modelsLibrary: List[PrinterModelMeta] = [
    {
        "model": PrinterModel.B3S_P,
        "generation": PrintGeneration.V4,
        "id": [272],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 576,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.T2S,
        "generation": PrintGeneration.V4,
        "id": [53250],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 832,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK],
    },
    {
        "model": PrinterModel.N1,
        "generation": PrintGeneration.V4,
        "id": [3586],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 120,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.HEAT_SHRINK_TUBE, LabelType.TRANSPARENT, LabelType.BLACK_MARK_GAP],
    },
    {
        "model": PrinterModel.TP2M_H,
        "generation": PrintGeneration.V4,
        "id": [4609],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 591,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B31,
        "generation": PrintGeneration.V4,
        "id": [5632],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 600,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B21_PRO,
        "generation": PrintGeneration.V5,
        "id": [785],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 591,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B2_PRO,
        "generation": PrintGeneration.V5,
        "id": [6912],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 567,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B2,
        "generation": PrintGeneration.V4,
        "id": [6913],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B18S,
        "generation": PrintGeneration.V4,
        "id": [3585],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 120,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.BLACK_MARK_GAP, LabelType.HEAT_SHRINK_TUBE],
    },
    {
        "model": PrinterModel.D11_H,
        "generation": PrintGeneration.V5,
        "id": [528],
        "dpi": 300,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 178,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B21_H,
        "generation": PrintGeneration.V4,
        "id": [784],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 567,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.CONTINUOUS, LabelType.BLACK],
    },
    {
        "model": PrinterModel.HI_D110,
        "generation": PrintGeneration.V4,
        "id": [2305],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 120,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.D110_M,
        "generation": PrintGeneration.V5,
        "id": [2320],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 120,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.M2_H,
        "generation": PrintGeneration.V4,
        "id": [4608],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 591,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.BLACK, LabelType.BLACK_MARK_GAP],
    },
    {
        "model": PrinterModel.A20,
        "generation": PrintGeneration.V4,
        "id": [2817],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 400,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.MP3K_W,
        "generation": PrintGeneration.V4,
        "id": [4867],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 656,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.A203,
        "generation": PrintGeneration.V4,
        "id": [2818],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 400,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.MP3K,
        "generation": PrintGeneration.V4,
        "id": [4866],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 656,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.K3_W,
        "generation": PrintGeneration.V4,
        "id": [4865],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 656,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.K3,
        "generation": PrintGeneration.V4,
        "id": [4864],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 656,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.BETTY,
        "generation": PrintGeneration.V4,
        "id": [2561],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 192,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.T8S,
        "generation": PrintGeneration.V4,
        "id": [2053],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 851,
        "paperTypes": [LabelType.WITH_GAPS],
    },
    {
        "model": PrinterModel.B21S,
        "generation": PrintGeneration.D110,
        "id": [777],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B21_L2B,
        "generation": PrintGeneration.V4,
        "id": [769],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.D11S,
        "generation": PrintGeneration.OLD_D11,
        "id": [514],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 96,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.A63,
        "generation": PrintGeneration.V4,
        "id": [2054],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 851,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.BLACK],
    },
    {
        "model": PrinterModel.FUST,
        "generation": PrintGeneration.V4,
        "id": [513],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 96,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.P1,
        "generation": PrintGeneration.V4,
        "id": [1024],
        "dpi": 300,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 697,
        "paperTypes": [LabelType.PVC_TAG],
    },
    {
        "model": PrinterModel.P18,
        "generation": PrintGeneration.V4,
        "id": [1026],
        "dpi": 300,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 662,
        "paperTypes": [LabelType.PVC_TAG],
    },
    {
        "model": PrinterModel.S6,
        "generation": PrintGeneration.V4,
        "id": [257, 258, 259, 260, 261, 262],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 576,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B21S_C2B,
        "generation": PrintGeneration.D110,
        "id": [776],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.P1S,
        "generation": PrintGeneration.V4,
        "id": [1025],
        "dpi": 300,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 697,
        "paperTypes": [LabelType.PVC_TAG],
    },
    {
        "model": PrinterModel.B1,
        "generation": PrintGeneration.V4,
        "id": [4096],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B1_PRO,
        "generation": PrintGeneration.V4,
        "id": [4097],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 567,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.A8,
        "generation": PrintGeneration.V4,
        "id": [256],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 600,
        "paperTypes": [LabelType.BLACK, LabelType.WITH_GAPS, LabelType.CONTINUOUS],
    },
    {
        "model": PrinterModel.B21_C2B,
        "generation": PrintGeneration.V4,
        "id": [771, 775],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.CONTINUOUS, LabelType.TRANSPARENT, LabelType.BLACK],
    },
    {
        "model": PrinterModel.Z401,
        "generation": PrintGeneration.V4,
        "id": [2051],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 851,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B16,
        "generation": PrintGeneration.V4,
        "id": [1792],
        "dpi": 203,
        # Print direction 270 in vendor DB; modelled as LEFT for now.
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 96,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B32R,
        "generation": PrintGeneration.V4,
        "id": [2050],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 851,
        "paperTypes": [LabelType.WITH_GAPS],
    },
    {
        "model": PrinterModel.B32,
        "generation": PrintGeneration.V4,
        "id": [2049],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 851,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.S3,
        "generation": PrintGeneration.V4,
        "id": [51460],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.JC_M90,
        "generation": PrintGeneration.V4,
        "id": [51461],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.JCB3S,
        "generation": PrintGeneration.V4,
        "id": [256],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 576,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B203,
        "generation": PrintGeneration.V4,
        "id": [2816],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 400,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.S1,
        "generation": PrintGeneration.V4,
        "id": [51458],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.D110,
        "generation": PrintGeneration.D110,
        "id": [2304, 2305],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 96,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B21,
        "generation": PrintGeneration.V4,
        "id": [768],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.D101,
        "generation": PrintGeneration.V4,
        "id": [2560],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 192,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.HI_NB_D11,
        "generation": PrintGeneration.V4,
        "id": [512],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 120,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.A8_P,
        "generation": PrintGeneration.V4,
        "id": [273],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 616,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.S6_P,
        "generation": PrintGeneration.V4,
        "id": [274],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 600,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.T6,
        "generation": PrintGeneration.V4,
        "id": [51715],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.B50W,
        "generation": PrintGeneration.V4,
        "id": [51714],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.T7,
        "generation": PrintGeneration.V4,
        "id": [51717],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.T8,
        "generation": PrintGeneration.V4,
        "id": [51718],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 567,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.B3S,
        "generation": PrintGeneration.V4,
        "id": [256, 260, 262],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 576,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B3,
        "generation": PrintGeneration.V4,
        "id": [52993],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 600,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B18,
        "generation": PrintGeneration.V4,
        "id": [3584],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 120,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.BLACK_MARK_GAP, LabelType.HEAT_SHRINK_TUBE],
    },
    {
        "model": PrinterModel.D11,
        "generation": PrintGeneration.OLD_D11,
        "id": [512],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 96,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.D11_PRO,
        "generation": PrintGeneration.V5,
        "id": [531],
        "dpi": 300,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 142,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B11,
        "generation": PrintGeneration.V4,
        "id": [51457],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED, LabelType.TRANSPARENT],
    },
    {
        "model": PrinterModel.B50,
        "generation": PrintGeneration.V4,
        "id": [51713],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 400,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.CONTINUOUS, LabelType.PERFORATED],
    },
    {
        "model": PrinterModel.ET10,
        "generation": PrintGeneration.V4,
        "id": [5376],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 1600,
        "paperTypes": [LabelType.CONTINUOUS],
    },
    {
        "model": PrinterModel.H1,
        "generation": PrintGeneration.V4,
        "id": [3840],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 96,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.B1_SE,
        "generation": PrintGeneration.V4,
        "id": [4098],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 384,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.H1S,
        "generation": PrintGeneration.V4,
        "id": [4352],
        "dpi": 203,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 96,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.CONTINUOUS, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.EP2M_H,
        "generation": PrintGeneration.V4,
        "id": [4610],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 591,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.BLACK, LabelType.BLACK_MARK_GAP],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.K3_ITD,
        "generation": PrintGeneration.V4,
        "id": [4868],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 656,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.C1,
        "generation": PrintGeneration.V4,
        "id": [5120],
        "dpi": 300,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 178,
        "paperTypes": [LabelType.CONTINUOUS],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.EP1C,
        "generation": PrintGeneration.V4,
        "id": [5121],
        "dpi": 300,
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 178,
        "paperTypes": [LabelType.CONTINUOUS],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.K2,
        "generation": PrintGeneration.V4,
        "id": [6144],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 480,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.M3,
        "generation": PrintGeneration.V4,
        "id": [6400],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 851,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.BLACK, LabelType.BLACK_MARK_GAP],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.EP3M,
        "generation": PrintGeneration.V4,
        "id": [6402],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 851,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.TRANSPARENT, LabelType.BLACK, LabelType.BLACK_MARK_GAP],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.B4,
        "generation": PrintGeneration.V4,
        "id": [6656],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 832,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.B4_PRO,
        "generation": PrintGeneration.V4,
        "id": [6657],
        "dpi": 300,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 1248,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.K4,
        "generation": PrintGeneration.V4,
        "id": [7168],
        "dpi": 203,
        "printDirection": PrintDirection.TOP,
        "printheadPixels": 656,
        "paperTypes": [LabelType.WITH_GAPS, LabelType.BLACK, LabelType.TRANSPARENT],
        "printheadPixelsEstimated": True,
    },
    {
        "model": PrinterModel.A1_PRO,
        "generation": PrintGeneration.V4,
        "id": [7424],
        "dpi": 300,
        # Print direction 270 in vendor DB; modelled as LEFT for now.
        "printDirection": PrintDirection.LEFT,
        "printheadPixels": 178,
        "paperTypes": [LabelType.PERFORATED, LabelType.CONTINUOUS],
        "printheadPixelsEstimated": True,
    },
]

# Density / RFID capabilities keyed by printer model ID (from devices.md).
_CAPABILITIES_BY_ID: dict[int, tuple[RfidClass, int, int, int]] = {
    256: (RfidClass.NONE, 1, 5, 3),
    257: (RfidClass.NONE, 1, 5, 3),
    258: (RfidClass.NONE, 1, 5, 3),
    259: (RfidClass.NONE, 1, 5, 3),
    260: (RfidClass.NONE, 1, 5, 3),
    261: (RfidClass.NONE, 1, 5, 3),
    262: (RfidClass.NONE, 1, 5, 3),
    272: (RfidClass.LABEL, 1, 5, 3),
    273: (RfidClass.LABEL, 1, 5, 3),
    274: (RfidClass.LABEL, 1, 5, 3),
    512: (RfidClass.LABEL, 1, 3, 2),
    513: (RfidClass.LABEL, 1, 5, 3),
    514: (RfidClass.LABEL, 1, 3, 2),
    528: (RfidClass.LABEL, 1, 5, 3),
    531: (RfidClass.LABEL, 1, 5, 3),
    768: (RfidClass.LABEL, 1, 5, 3),
    769: (RfidClass.LABEL, 1, 5, 3),
    771: (RfidClass.LABEL, 1, 5, 3),
    775: (RfidClass.LABEL, 1, 5, 3),
    776: (RfidClass.LABEL, 1, 5, 3),
    777: (RfidClass.LABEL, 1, 5, 3),
    784: (RfidClass.LABEL, 1, 5, 3),
    785: (RfidClass.LABEL, 1, 5, 3),
    1024: (RfidClass.RIBBON, 1, 5, 3),
    1025: (RfidClass.RIBBON, 1, 5, 3),
    1026: (RfidClass.RIBBON, 1, 5, 3),
    1792: (RfidClass.LABEL, 1, 3, 2),
    2049: (RfidClass.RIBBON, 1, 15, 10),
    2050: (RfidClass.RIBBON, 1, 15, 10),
    2051: (RfidClass.RIBBON, 1, 15, 10),
    2053: (RfidClass.NONE, 1, 15, 10),
    2054: (RfidClass.RIBBON, 1, 15, 10),
    2304: (RfidClass.LABEL, 1, 3, 2),
    2305: (RfidClass.LABEL, 1, 3, 2),
    2320: (RfidClass.LABEL, 1, 5, 3),
    2560: (RfidClass.LABEL, 1, 3, 2),
    2561: (RfidClass.LABEL, 1, 3, 2),
    2816: (RfidClass.LABEL, 1, 5, 3),
    2817: (RfidClass.LABEL, 1, 5, 3),
    2818: (RfidClass.LABEL, 1, 5, 3),
    3584: (RfidClass.LABEL_RIBBON, 1, 3, 2),
    3585: (RfidClass.LABEL_RIBBON, 1, 3, 2),
    3586: (RfidClass.LABEL_RIBBON, 1, 3, 2),
    3840: (RfidClass.LABEL, 1, 3, 2),
    4096: (RfidClass.LABEL, 1, 5, 3),
    4097: (RfidClass.LABEL, 1, 5, 3),
    4098: (RfidClass.LABEL, 1, 5, 3),
    4352: (RfidClass.LABEL, 1, 3, 2),
    4608: (RfidClass.LABEL_RIBBON, 1, 5, 3),
    4609: (RfidClass.LABEL_RIBBON, 1, 5, 3),
    4610: (RfidClass.LABEL_RIBBON, 1, 5, 3),
    4864: (RfidClass.LABEL, 1, 5, 3),
    4865: (RfidClass.LABEL, 1, 5, 3),
    4866: (RfidClass.LABEL, 1, 5, 3),
    4867: (RfidClass.LABEL, 1, 5, 3),
    4868: (RfidClass.LABEL, 1, 5, 3),
    5120: (RfidClass.RIBBON, 1, 5, 3),
    5121: (RfidClass.RIBBON, 1, 5, 3),
    5376: (RfidClass.NONE, 3, 3, 3),
    5632: (RfidClass.LABEL, 1, 5, 3),
    6144: (RfidClass.LABEL, 1, 5, 3),
    6400: (RfidClass.LABEL_RIBBON, 1, 5, 3),
    6402: (RfidClass.LABEL_RIBBON, 1, 5, 3),
    6656: (RfidClass.LABEL, 1, 5, 3),
    6657: (RfidClass.LABEL, 1, 5, 3),
    6912: (RfidClass.LABEL, 1, 5, 3),
    6913: (RfidClass.LABEL, 1, 5, 3),
    7168: (RfidClass.LABEL, 1, 15, 7),
    7424: (RfidClass.NONE, 1, 5, 3),
    51457: (RfidClass.NONE, 6, 15, 10),
    51458: (RfidClass.NONE, 6, 15, 10),
    51460: (RfidClass.NONE, 6, 15, 10),
    51461: (RfidClass.NONE, 6, 15, 10),
    51713: (RfidClass.NONE, 6, 15, 10),
    51714: (RfidClass.NONE, 6, 15, 10),
    51715: (RfidClass.NONE, 6, 15, 10),
    51717: (RfidClass.NONE, 6, 15, 10),
    51718: (RfidClass.NONE, 6, 15, 10),
    52993: (RfidClass.NONE, 1, 5, 3),
    53250: (RfidClass.NONE, 1, 20, 15),
}

_DEFAULT_CAPS = (RfidClass.NONE, 1, 5, 3)

_LABEL_TYPE_NAMES = {
    1: "WithGaps",
    2: "Black",
    3: "Continuous",
    4: "Perforated",
    5: "Transparent",
    6: "PvcTag",
    10: "BlackMarkGap",
    11: "HeatShrinkTube",
}

_LABEL_TYPE_CODES = {
    LabelType.WITH_GAPS: 1,
    LabelType.BLACK: 2,
    LabelType.CONTINUOUS: 3,
    LabelType.PERFORATED: 4,
    LabelType.TRANSPARENT: 5,
    LabelType.PVC_TAG: 6,
    LabelType.BLACK_MARK_GAP: 10,
    LabelType.HEAT_SHRINK_TUBE: 11,
}


def consumable_type_name(type_code: int | None) -> str | None:
    if type_code is None:
        return None
    return _LABEL_TYPE_NAMES.get(type_code, f"Unknown({type_code})")


_MATERIAL_NAMES: dict[int, str] = {
    1: "Thermal synthetic paper, general",
    2: "Tag / nameplate",
    3: "PP synthetic paper",
    4: "Thermal card stock",
    5: "Transparent PET",
    6: "Coated paper",
    7: "Coated card stock",
    8: "Matte silver PET",
    9: "White PET",
    10: "White PVC",
    11: "Triple-resistant thermal paper",
    12: "PP card stock",
    13: "Transparent PE",
    14: "White PE",
    15: "Pearlescent synthetic paper",
    18: "Matte black PET",
    19: "Transparent thermal",
    21: "Hot stamping foil",
    22: "Transparent PP, cable wrap",
    23: "White cryogenic",
    28: "Thermal synthetic paper, red imaging",
    29: "Thermal synthetic paper, red/black",
    31: "Thermal synthetic paper, low temperature",
    35: "PET card stock",
    37: "Satin ribbon",
    53: "Heat-shrink tubing",
    54: "Wire marker sleeve",
    55: "Transparent PP, general",
    64: "Thermal synthetic paper, thick",
    65: "Thermal synthetic paper, writable",
    67: "PP synthetic paper, writable",
    70: "Thermal synthetic paper, greyscale",
    80: "Thermal synthetic paper, red/black, thick",
    93: "Matte white PET",
    103: "Transparent PVC, electrostatic cling",
    110: "Thermal synthetic paper, flexible",
    129: "PVC tag",
}


def material_name(type_code: int | None) -> str | None:
    if type_code is None:
        return None
    return _MATERIAL_NAMES.get(type_code, f"Unknown({type_code})")


# PrinterInfo AutoShutdownTime is an index, not minutes (model-dependent).
# Option values are stable translation keys (see entity.select.auto_shutdown.state).
AUTO_SHUTDOWN_OPTIONS: dict[int, str] = {
    1: "15_min",
    2: "30_min",
    3: "45_60_min",
    4: "60_min_never",
}


def auto_shutdown_option(index: int | None) -> str | None:
    """Return the select option key for a PrinterInfo auto-shutdown index."""
    if index is None:
        return None
    return AUTO_SHUTDOWN_OPTIONS.get(int(index))


def auto_shutdown_index(option: str) -> int | None:
    for index, key in AUTO_SHUTDOWN_OPTIONS.items():
        if key == option:
            return index
    return None


# Back-compat alias used by older call sites.
def auto_shutdown_label(index: int | None) -> str | None:
    return auto_shutdown_option(index)


def label_type_code(label_type: LabelType) -> int:
    return _LABEL_TYPE_CODES[label_type]


def supports_label_rfid(rfid: RfidClass | None) -> bool:
    return rfid in (RfidClass.LABEL, RfidClass.LABEL_RIBBON)


def supports_ribbon_rfid(rfid: RfidClass | None) -> bool:
    return rfid in (RfidClass.RIBBON, RfidClass.LABEL_RIBBON)


def _enrich_meta(meta: PrinterModelMeta) -> PrinterModelMeta:
    """Fill rfid / density fields from the ID capability table."""
    out: PrinterModelMeta = dict(meta)  # type: ignore[assignment]
    caps = _DEFAULT_CAPS
    for pid in meta["id"]:
        if pid in _CAPABILITIES_BY_ID:
            caps = _CAPABILITIES_BY_ID[pid]
            break
    rfid, dmin, dmax, ddef = caps
    out.setdefault("rfid", rfid)
    out.setdefault("densityMin", dmin)
    out.setdefault("densityMax", dmax)
    out.setdefault("densityDefault", ddef)
    return out


def get_printer_meta_by_id(printer_id: int) -> Union[PrinterModelMeta, None]:
    for model in modelsLibrary:
        if printer_id in model["id"]:
            return _enrich_meta(model)
    return None

def get_printer_meta_by_model(model: PrinterModel) -> Union[PrinterModelMeta, None]:
    for m in modelsLibrary:
        if m["model"] == model:
            return _enrich_meta(m)
    return None
