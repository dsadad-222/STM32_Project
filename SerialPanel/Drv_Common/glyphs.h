/**
  ******************************************************************************
  * @file    Drv_Common/glyphs.h
  * @brief   Fixed 8x8 bitmap font covering the printable ASCII range.
  *
  *          Each entry holds 8 bytes, one byte per row, MSB is the left
  *          most pixel of that row.
  ******************************************************************************
  */

#ifndef GLYPHS_H
#define GLYPHS_H

#include <stdint.h>

#define GLYPH_FIRST     0x20U       /* ' ' */
#define GLYPH_LAST      0x7EU       /* '~' */
#define GLYPH_W         8U          /* cell width in pixels  */
#define GLYPH_H         8U          /* cell height in pixels */

extern const uint8_t g_glyph_8x8[GLYPH_LAST - GLYPH_FIRST + 1U][GLYPH_H];

#endif /* GLYPHS_H */
