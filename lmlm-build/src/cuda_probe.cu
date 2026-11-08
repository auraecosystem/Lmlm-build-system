#include <cuda_runtime.h>
#include <iostream>

__global__ void lmlm_cuda_probe_kernel(int* value) {
  if (blockIdx.x == 0 && threadIdx.x == 0) *value = 42;
}

int main() {
  int count = 0;
  const cudaError_t status = cudaGetDeviceCount(&count);
  if (status != cudaSuccess || count == 0) {
    std::cout << "{\"backend\":\"cuda\",\"available\":false,\"devices\":0}\n";
    (void)cudaGetLastError();
    return 0;
  }
  int value = 0;
  int* device_value = nullptr;
  if (cudaMalloc(&device_value, sizeof(int)) != cudaSuccess) return 2;
  lmlm_cuda_probe_kernel<<<1, 1>>>(device_value);
  cudaError_t result = cudaGetLastError();
  if (result == cudaSuccess) result = cudaMemcpy(&value, device_value, sizeof(int), cudaMemcpyDeviceToHost);
  cudaFree(device_value);
  if (result != cudaSuccess || value != 42) return 3;
  std::cout << "{\"backend\":\"cuda\",\"available\":true,\"devices\":" << count
            << ",\"kernel_probe\":\"passed\"}\n";
  return 0;
}
