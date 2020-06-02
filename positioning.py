import config
###################
# Font colors
###################
color = {}
#color["inactive"]   = 70,65,62
color["inactive"]   = 50,46,44
color["text"]       = 230,228,227
color["highlight"]  = 230,228,0

###################
# Sizes
###################
size = {}
size["margin"]               = 4,4
size["padding"]              = 4,4
size["coverart"]             = 256, 256
size["topmenu"]              = 80
size["bottommenu"]           = 60
size["selectorbutton"]       = 64, 64
size["controlbutton"]        = 48, 48
size["button_screenoff"]     = 60, 60
size["icon_screenoff"]       = 20, 16
size["togglebutton"]         = 62, 25
size["volume_text_width"]    = 46
size["volume_field"]         = 44, 24
size["volume_fieldoffset"]   = 6
size["trackinfo_height"]     = 20 # Row height
size["details"]              = 46,52
size["elapsed"]              = 40,40
size["elapsedmargin"]        = 6
size["elapsedoffset"]        = 7
size["controlbuttonsoffset"] = 16
size["progressbar"]          = 370, 8
size["progressbar_height"]   = 16
size["progressbar_click"]    = size["progressbar"][0], 60
size["volume_click"]         = 80,260
size["volume_slider"]        = 20,180
size["listitem_height"]      = 34
size["logo"]                 = 34, 34
size["logoback"]             = size["logo"][0]+2*size["margin"][0]+2*size["padding"][0] , size["logo"][1]+2*size["margin"][1]+2*size["padding"][1]
size["screen"]               = config.resolution[0] - 2*size["margin"][0], config.resolution[1]-2*size["margin"][1]
size["paddedscreen"]         = size["screen"][0] - 2*size["padding"][0], size["screen"][1] - 2*size["padding"][1]
size["scrollbar"]            = 20, size["screen"][1]
size["scrollbar_click"]      = 60, config.resolution[1]
size["scrollbar_slider"]     = 20, size["scrollbar"][1]-28
size["listbutton"]           = 20, 20



###################
# positioning
###################
_pos = {}

# Screen borders
_pos["left"]         = size   ["margin"][0]
_pos["right"]        = config.resolution[0]  - size["margin"] [0]
_pos["top"]          = size   ["margin"][1]
_pos["bottom"]       = config.resolution[1]  - size["margin"][1]
_pos["paddedleft"]   = _pos    ["left"]       + size["padding"][0]
_pos["paddedright"]  = _pos    ["right"]      - size["padding"][0]
_pos["paddedtop"]    = _pos    ["top"]        + size["padding"][1]
_pos["paddedbottom"] = _pos    ["bottom"]     - size["padding"][1]
_pos["center"]       = config.resolution[0]/2, config.resolution[1]/2

# Text
_pos["topmenu"]      = 0, _pos["top"]-size["topmenu"]+10
_pos["bottommenu"]   = 0, _pos["bottom"]+20

_pos["MAIN"]         = _pos["center"][0], _pos["top"]-30
_pos["testtext"]     = _pos["center"][0], _pos["bottom"]
_pos["listview"]     = _pos["paddedleft"], _pos["paddedtop"]

# Track info
_pos["track"]              = _pos["left"] + size["elapsedmargin"], _pos["bottom"] - size["trackinfo_height"]
_pos["album"]              = _pos["track"][0], _pos["track"][1] - size["trackinfo_height"]
_pos["progressbar"]        = _pos["left"] + size["elapsed"][0] + 11, _pos["album"][1] - 12
_pos["elapsed"]            = _pos["left"] + size["elapsedmargin"], _pos["progressbar"][1] - size["elapsedoffset"]
_pos["track_length"]       = _pos["right"] - size["elapsed"][0] - size["elapsedmargin"], _pos["progressbar"][1] - size["elapsedoffset"]

# Background refresh for track info
_pos["trackinfobackground"] = 0, _pos["progressbar"][1] - 4
size["trackinfobackground"] = config.resolution[0], config.resolution[1] - _pos["progressbar"][1] + 6

# Background refresh for elapsed information
_pos["progressbackground"] = 0, _pos["progressbar"][1] - 4
size["progressbackground"] = _pos["track_length"][0], size["progressbar_height"]

# Buttons
# Topmost selector button
_pos["buttonleft"]  = _pos["left"] + 28, _pos["progressbar"][1]-64 - size["controlbutton"][1] #418, 8
_pos["buttonright"] = _pos["right"] - size["controlbutton"][0], _pos["paddedtop"] #418, 8

_pos["repeatbutton"]  = _pos["buttonleft"]
_pos["randombutton"]  = _pos["repeatbutton"][0], _pos["repeatbutton"][1] - size["selectorbutton"][1]

_pos["volume"]         = _pos["right"]-size["volume_click"][0]/2-15, 30
_pos["volume_click"]   = _pos["volume"][0]-size["volume_click"][0]/2, _pos["volume"][1]-30
_pos["volume_slider"]  = _pos["volume"][0]+2, _pos["volume"][1]+4

_pos["icon_screenoff"] = config.resolution[0] - size["icon_screenoff"][0]-5    , config.resolution[1] - size["icon_screenoff"][1]-5

# Cover art
_pos["coverart"]      = (config.resolution[0] - size["coverart"][0])/2, _pos["top"] #4

# Player icon
_pos["logo"]          = _pos["paddedright"] - size["logo"][0], _pos["paddedbottom"] - size["logo"][1]
_pos["logoback"]      = _pos["logo"][0] - size["padding"][0], _pos["logo"][1] - size["padding"][1]

# List view
_pos["scrollbar"]        = _pos["right"] -size["scrollbar"][0]/2 - 2, _pos["top"]
_pos["scrollbar_click"]  = _pos["scrollbar"][0]-size["scrollbar_click"][0], 0
_pos["scrollbar_slider"] = _pos["scrollbar"][0]+4, _pos["scrollbar"][1]+12

###########################
# Helper functions
###########################
def limit(value,min,max):
    value = max if value > max else value
    value = min if value < min else value
    return value

def limit_offset(offset,max=(-config.resolution[0],-config.resolution[1],config.resolution[0],config.resolution[1])):
    if offset[0] > 0:
        offset = (max[2] if offset[0] > max[2] else offset[0],
                  offset[1])
    else:
        offset = (max[0] if offset[0] < max[0] else offset[0],
                  offset[1])
    if offset[1] > 0:
        offset = (offset[0],
                  max[3] if offset[1] > max[3] else offset[1])
    else:
        offset = (offset[0],
                 max[1] if offset[1] < max[1] else offset[1])
    return offset

def render_menuitem(text, font, color_str, menu, index, offset, direction="up"):

    if direction == "down":
        offset = (offset[0], offset[1] + index*size[menu])
    if direction == "up":
        offset = (offset[0], offset[1] - index*size[menu])

    text = _render_text(text, font, color_str)

    text_rect = text.get_rect(center=(config.resolution[0]/2, 0))
    offset = (offset[0] - text_rect[0], offset[1])
    position = pos(menu, offset)

    return (text,position)

def menupos(item, number, offset, direction="down"):
    if direction == "down":
        offset = (offset[0], offset[1] + number*size[item])
    if direction == "up":
        offset = (offset[0], offset[1] - number*size[item])
    return pos(item, offset)

def pos(position, offset=(0,0)):
    return _pos[position][0] + offset[0], _pos[position][1] + offset[1]

def render_text(text, font, color_str="text"):
    return font.render(text, 1, color[color_str])

# Compare if between x_0,y_0 and x_1,y_1
def clicked(click, start__pos, size):
    return start__pos[0] <= click[0] <= start__pos[0] + size[0] and \
       start__pos[1] <= click[1] <= start__pos[1] + size[1]

