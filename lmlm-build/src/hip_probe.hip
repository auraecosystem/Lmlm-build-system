#include <hip/hip_runtime.h>
extern "C" __global__ void lmlm_hip_build_probe(int* output) {
  if (blockIdx.x == 0 && threadIdx.x == 0) *output = 1;
}
