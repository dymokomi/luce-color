// sRGB's transfer function (IEC 61966-2-1), for the shaders that mix colors
// as Photoshop does: tiles hold linear light, and a document that blends in
// sRGB (the default; "Blend RGB Colors Using Gamma 1.0" off) encodes what it
// mixes, mixes, and decodes the result. Values past 1 follow the curve;
// negative ones stay on its linear foot, so the two are inverses everywhere.
vec3 srgb_encode(vec3 c) {
    vec3 curve = 1.055 * pow(max(c, vec3(0.0031308)), vec3(1.0 / 2.4)) - 0.055;
    return mix(c * 12.92, curve, step(vec3(0.0031308), c));
}
vec3 srgb_decode(vec3 c) {
    vec3 curve = pow(max((c + 0.055) / 1.055, vec3(0.04045 / 12.92)), vec3(2.4));
    return mix(c / 12.92, curve, step(vec3(0.04045), c));
}
