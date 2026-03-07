from enum import IntFlag

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 as __wrapper_module__
from comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 import (
    OLE_YPOS_PIXELS, IPictureDisp, IEnumVARIANT, OLE_OPTEXCLUSIVE,
    OLE_XPOS_CONTAINER, OLE_XSIZE_HIMETRIC, OLE_XSIZE_PIXELS,
    OLE_XSIZE_CONTAINER, HRESULT, Unchecked, Font, FONTBOLD, IUnknown,
    IFontDisp, DISPMETHOD, _lcid, Library, EXCEPINFO, Default,
    IFontEventsDisp, _check_version, FONTNAME, IFont, StdPicture,
    FONTSTRIKETHROUGH, OLE_YSIZE_HIMETRIC, GUID, OLE_HANDLE, Color,
    FONTSIZE, FONTUNDERSCORE, Gray, OLE_COLOR, Monochrome, VgaColor,
    OLE_YPOS_HIMETRIC, OLE_YSIZE_PIXELS, OLE_XPOS_PIXELS,
    VARIANT_BOOL, IDispatch, DISPPARAMS, OLE_ENABLEDEFAULTBOOL,
    Picture, FONTITALIC, CoClass, BSTR, OLE_YSIZE_CONTAINER,
    typelib_path, OLE_YPOS_CONTAINER, dispid, IPicture, FontEvents,
    StdFont, Checked, COMMETHOD, OLE_CANCELBOOL, OLE_XPOS_HIMETRIC,
    DISPPROPERTY
)


class OLE_TRISTATE(IntFlag):
    Unchecked = 0
    Checked = 1
    Gray = 2


class LoadPictureConstants(IntFlag):
    Default = 0
    Monochrome = 1
    VgaColor = 2
    Color = 4


__all__ = [
    'FONTSIZE', 'OLE_YPOS_PIXELS', 'OLE_TRISTATE', 'FONTUNDERSCORE',
    'IPictureDisp', 'OLE_OPTEXCLUSIVE', 'Gray', 'OLE_COLOR',
    'Monochrome', 'VgaColor', 'LoadPictureConstants',
    'OLE_XPOS_CONTAINER', 'OLE_XSIZE_HIMETRIC', 'OLE_YPOS_HIMETRIC',
    'OLE_YSIZE_PIXELS', 'OLE_XPOS_PIXELS', 'OLE_XSIZE_PIXELS',
    'OLE_XSIZE_CONTAINER', 'OLE_ENABLEDEFAULTBOOL', 'Unchecked',
    'Font', 'FONTBOLD', 'IFontDisp', 'Picture', 'FONTITALIC',
    'Library', 'OLE_YSIZE_CONTAINER', 'typelib_path',
    'OLE_YPOS_CONTAINER', 'Default', 'IFontEventsDisp', 'IPicture',
    'FontEvents', 'StdFont', 'Checked', 'OLE_CANCELBOOL', 'FONTNAME',
    'IFont', 'StdPicture', 'FONTSTRIKETHROUGH', 'OLE_YSIZE_HIMETRIC',
    'OLE_XPOS_HIMETRIC', 'OLE_HANDLE', 'Color'
]

