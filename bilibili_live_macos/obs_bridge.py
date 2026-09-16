"""OBS 32 API 兼容层。

上层代码不要直接依赖 obspython 的细节，统一通过这里调用。
"""

import obspython as obs


_BUTTON_HANDLERS = {}


def _modified_dispatcher(props, prop, settings):
    """信息型控件的统一 modified 回调，返回 True 让 OBS 刷新控件。"""
    return True


def enum_value(value) -> int:
    """把 OBS 枚举常量规范化为整数，兼容不同版本的枚举绑定。"""
    return int(value)


def create_properties():
    return obs.obs_properties_create()


def add_group(parent, name, description, child_properties):
    return obs.obs_properties_add_group(
        parent,
        name,
        description,
        enum_value(obs.OBS_GROUP_NORMAL),
        child_properties,
    )


def add_text(props, name, description, text_type=None):
    if text_type is None:
        text_type = obs.OBS_TEXT_DEFAULT
    return obs.obs_properties_add_text(
        props,
        name,
        description,
        enum_value(text_type),
    )


def add_info_text(props, name, description):
    prop = obs.obs_properties_add_text(
        props,
        name,
        description,
        enum_value(obs.OBS_TEXT_INFO),
    )
    obs.obs_property_text_set_info_type(
        prop,
        enum_value(obs.OBS_TEXT_INFO_NORMAL),
    )
    if hasattr(obs, "obs_property_set_modified_callback"):
        obs.obs_property_set_modified_callback(prop, _modified_dispatcher)
    return prop


def add_bool(props, name, description):
    return obs.obs_properties_add_bool(props, name, description)


def add_int(props, name, description, minimum, maximum, step):
    return obs.obs_properties_add_int(
        props,
        name,
        description,
        int(minimum),
        int(maximum),
        int(step),
    )


def add_list(props, name, description, list_type=None, value_format=None):
    if list_type is None:
        list_type = obs.OBS_COMBO_TYPE_LIST
    if value_format is None:
        value_format = obs.OBS_COMBO_FORMAT_STRING
    return obs.obs_properties_add_list(
        props,
        name,
        description,
        enum_value(list_type),
        enum_value(value_format),
    )


def list_clear(prop):
    obs.obs_property_list_clear(prop)


def list_add_string(prop, label, value):
    obs.obs_property_list_add_string(prop, str(label), str(value))


def _button_clicked(props, prop):
    """所有按钮共享的入口回调。

    OBS 的脚本回调要求传入模块级函数，不能直接传实例方法或 lambda。
    这里只负责按按钮名分发给真实处理器，OBS 看到的始终是这个固定函数。
    """
    name = obs.obs_property_name(prop)
    handler = _BUTTON_HANDLERS.get(name)
    if handler is None:
        return False
    return bool(handler(props, prop))


def add_button(props, name, description, callback):
    if not hasattr(obs, "obs_properties_add_button"):
        raise RuntimeError(
            "当前 OBS 版本没有提供脚本可用的 obs_properties_add_button"
        )

    _BUTTON_HANDLERS[name] = callback
    return obs.obs_properties_add_button(
        props,
        name,
        description,
        _button_clicked,
    )


def set_button_url(prop, url):
    obs.obs_property_button_set_url(prop, url)


def get_streaming_service():
    return obs.obs_frontend_get_streaming_service()


def get_service_settings(service):
    return obs.obs_service_get_settings(service)


def update_service(service, settings):
    obs.obs_service_update(service, settings)


def save_streaming_service():
    obs.obs_frontend_save_streaming_service()


def streaming_active():
    return bool(obs.obs_frontend_streaming_active())


def start_streaming():
    obs.obs_frontend_streaming_start()


def stop_streaming():
    obs.obs_frontend_streaming_stop()


def release_data(data):
    obs.obs_data_release(data)


def timer_add(callback, milliseconds):
    obs.timer_add(callback, int(milliseconds))


def timer_remove(callback):
    obs.timer_remove(callback)


def apply_settings(props, settings):
    obs.obs_properties_apply_settings(props, settings)


def button_clicked(prop, obj=None):
    return obs.obs_property_button_clicked(prop, obj)


def set_modified_callback(prop):
    if hasattr(obs, "obs_property_set_modified_callback"):
        obs.obs_property_set_modified_callback(prop, _modified_dispatcher)


def set_visible(prop, visible):
    obs.obs_property_set_visible(prop, bool(visible))


def set_enabled(prop, enabled):
    obs.obs_property_set_enabled(prop, bool(enabled))


def get_string(settings, name, default=""):
    value = obs.obs_data_get_string(settings, name)
    return value if value is not None else default


def set_string(settings, name, value):
    obs.obs_data_set_string(settings, name, str(value))


def get_int(settings, name, default=0):
    value = obs.obs_data_get_int(settings, name)
    return value if value is not None else default


def set_int(settings, name, value):
    obs.obs_data_set_int(settings, name, int(value))


def get_bool(settings, name, default=False):
    value = obs.obs_data_get_bool(settings, name)
    return value if value is not None else default


def set_bool(settings, name, value):
    obs.obs_data_set_bool(settings, name, bool(value))


def log(level, message):
    obs.blog(enum_value(level), str(message))
