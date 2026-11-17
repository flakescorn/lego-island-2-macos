# Included after upstream variables. Local shared SDL and direct MoltenVK, no system Vulkan loader.
CC = clang
SDL3 = third_party/sdl3
MVK = third_party/MoltenVK/MoltenVK/dynamic/dylib/macOS
CFLAGS_COMMON += -Ithird_party/simde-0.8.2 -Ithird_party/Vulkan-Headers-vulkan-sdk-1.4.350.1/include -ffp-contract=off -gline-tables-only
CFLAGS_RT += -Wno-unknown-warning-option
LDFLAGS = -L$(SDL3)/lib -lSDL3 -L$(MVK) -lMoltenVK -pthread -lm -lz \
  -Wl,-rpath,@executable_path/../third_party/sdl3/lib \
  -Wl,-rpath,@executable_path/../Frameworks \
  -Wl,-rpath,@executable_path/../third_party/MoltenVK/MoltenVK/dynamic/dylib/macOS
