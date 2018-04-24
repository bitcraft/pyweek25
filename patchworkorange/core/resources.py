from pkg_resources import resource_listdir, resource_filename


def list_maps():
    print(resource_listdir('patchworkorange.assets.maps', ''))


def list_data():
    print(resource_listdir('patchworkorange.assets.data', ''))


def get_data_asset(name):
    return resource_filename('patchworkorange.assets.data', name)


def get_map_asset(name):
    return resource_filename('patchworkorange.assets.maps', name)


def get_image_asset(name):
    return resource_filename("patchworkorange.assets.images", name)


def get_font_asset(name):
    return resource_filename("patchworkorange.assets.fonts", name)


def get_sound_asset(name):
    return resource_filename("patchworkorange.assets.sounds", name)
