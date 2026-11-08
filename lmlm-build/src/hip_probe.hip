#include <hip/hip_runtime.h>
#include <iostream>

__global__ void lmlm_hip_probe_kernel(int* value) {
  if (blockIdx.x == 0 && threadIdx.x == 0) *value = 42;
}

int main() {
  int count = 0;
  const hipError_t status = hipGetDeviceCount(&count);
  if (status != hipSuccess || count == 0) {
    std::cout << "{\"backend\":\"rocm\",\"available\":false,\"devices\":0}\n";
    (void)hipGetLastError();
    return 0;
  }
  int value = 0;
  int* device_value = nullptr;
  if (hipMalloc(&device_value, sizeof(int)) != hipSuccess) return 2;
  hipLaunchKernelGGL(lmlm_hip_probe_kernel, dim3(1), dim3(1), 0, 0, device_value);
  hipError_t result = hipGetLastError();
  if (result == hipSuccess) result = hipMemcpy(&value, device_value, sizeof(int), hipMemcpyDeviceToHost);
  hipFree(device_value);
  if (result != hipSuccess || value != 42) return 3;
  std::cout << "{\"backend\":\"rocm\",\"available\":true,\"devices\":" << count
            << ",\"kernel_probe\":\"passed\"}\n";
  return 0;
}
