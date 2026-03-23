File "/mount/src/agente-pedidos-autosexito/app_PisosEspecializados.py", line 189, in <module>
    st.pyplot(fig)
    ~~~~~~~~~^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/metrics_util.py", line 532, in wrapped_func
    result = non_optional_func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/pyplot.py", line 174, in pyplot
    marshall(
    ~~~~~~~~^
        self.dg._get_delta_path_str(),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<4 lines>...
        **kwargs,
        ^^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/pyplot.py", line 226, in marshall
    marshall_images(
    ~~~~~~~~~~~~~~~^
        coordinates=coordinates,
        ^^^^^^^^^^^^^^^^^^^^^^^^
    ...<6 lines>...
        output_format="PNG",
        ^^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/lib/image_utils.py", line 445, in marshall_images
    proto_img.url = image_to_url(
                    ~~~~~~~~~~~~^
        single_image, layout_config, clamp, channels, output_format, image_id
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/lib/image_utils.py", line 337, in image_to_url
    image_data = _ensure_image_size_and_format(image_data, layout_config, image_format)
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/elements/lib/image_utils.py", line 186, in _ensure_image_size_and_format
    pil_image: PILImage = Image.open(io.BytesIO(image_data))
                          ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/PIL/Image.py", line 3558, in open
    im = _open_core(fp, filename, prefix, formats)
File "/home/adminuser/venv/lib/python3.14/site-packages/PIL/Image.py", line 3547, in _open_core
    _decompression_bomb_check(im.size)
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/PIL/Image.py", line 3448, in _decompression_bomb_check
    raise DecompressionBombError(msg)