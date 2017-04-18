import construct

accelerometer_data = construct.Struct(
    "accel_x" / construct.Int16sl,
    "accel_y" / construct.Int16sl,
    "accel_z" / construct.Int16sl
)

gyroscope_data = construct.BitStruct(
    "gyro_roll" / construct.BitsInteger(24),
    "gyro_yaw" / construct.BitsInteger(24),
    "gyro_pitch" / construct.BitsInteger(24)
)

magnet_data = construct.Struct(
    construct.Padding(6)
)

touchscreen_coords_data = construct.BitStruct(
    "touch_pad" / construct.Bit,
    "touch_extra" / construct.BitsInteger(3),
    "touch_value" / construct.BitsInteger(12)
)
touchscreen_points_data = construct.Struct(
    "coords" / construct.Array(2, touchscreen_coords_data)
)
touchscreen_data = construct.Struct(
    "points" / construct.Array(10, touchscreen_points_data)
)

input_data = construct.Struct(
    "sequence_id" / construct.Int16ub,
    "buttons" / construct.Int16ub,
    "power_status" / construct.Int8ub,
    "battery_charge" / construct.Int8ub,
    "left_stick_x" / construct.Int16ub,
    "left_stick_y" / construct.Int16ub,
    "right_stick_x" / construct.Int16ub,
    "right_stick_y" / construct.Int16ub,
    "audio_volume" / construct.Int8ub,
    construct.Embedded(accelerometer_data),
    construct.Embedded(gyroscope_data),
    construct.Embedded(magnet_data),
    construct.Embedded(touchscreen_data),
    "unkown_0" / construct.BytesInteger(4),
    "extra_buttons" / construct.Int8ub,
    "unknown_1" / construct.BytesInteger(46),
    "fw_version_neg" / construct.Int8ub
)
