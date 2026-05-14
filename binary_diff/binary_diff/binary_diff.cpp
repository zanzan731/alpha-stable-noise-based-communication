// binary_diff.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>
#include <fstream>
#include <bitset>

using namespace std;

int main()
{
    ifstream decoded("decoded.bin", ios::binary);
    ifstream source("source.bin", ios::binary);
    ofstream output;
    output.open("output.txt");
    if (!decoded || !source) {
        cerr << "Ne morem odpreti fila";
        return 1;
    }
    unsigned char b1, b2;
    size_t bytePosition = 0;
    size_t steviloRazlicnihBitov = 0;

    while (true) {
        bool r1 = static_cast<bool>(source.read(reinterpret_cast<char*>(&b1), 1));
        bool r2 = static_cast<bool>(decoded.read(reinterpret_cast<char*>(&b2), 1));

        if (r1 != r2) {
            cerr << "Datoteke niso enake velikosti\n";
            return 1;
        }

        if (!r1 && !r2) {
            cout << "Prisli smo do konca\n";
            output << "File stevilka ....: " << steviloRazlicnihBitov << "/" << bytePosition << "\n";
            return 0;
        }

        if (b1 == b2) {
            bytePosition += 8;
            continue;
        }
        for (int i = 7; i >= 0; --i) {
            int bit1 = (b1 >> i) & 1;
            int bit2 = (b2 >> i) & 1;
            if (bit1 == bit2) {
                bytePosition++;
                continue;
            }
            else {
                //cout << bytePosition << "\n";
                bytePosition++;
                steviloRazlicnihBitov++;
                continue;
            }
        
        }
        

    
    }

    

        return 1;
}
