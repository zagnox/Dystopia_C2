#ifndef c2file_H__
#define c2file_H__

#include <windows.h>

DWORD read_frame(HANDLE my_handle, char * buffer, DWORD max)
void write_frame(HANDLE my_handle, char * buffer, DWORD length)
HANDLE start_beacon(char * payload, DWORD length)

#endif