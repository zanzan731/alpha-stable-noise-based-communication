// binary_diff.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>
#include <fstream>
#include <bitset>
#include <string>

using namespace std;

int main()
{
    ofstream output;
    output.open("output.txt");
    size_t vsota_vseh_skupnih_napak = 0;
    int stevilo_datotek = 0;
    while (true) {

        int itteration = 0;
        nadaljuj:
        itteration++;
        
        ifstream decoded("decoded_" + to_string(itteration) + ".bin", ios::binary);
        ifstream source("source_" + to_string(itteration) + ".bin", ios::binary);
        
        if (!decoded || !source) {
            cerr << "Ne morem odpreti fila";
            stevilo_datotek = itteration - 1;
            goto konec;
        }
        unsigned char b1, b2;
        size_t bytePosition = 0;
        size_t steviloRazlicnihBitov = 0;

        while (true) {
            bool r1 = static_cast<bool>(source.read(reinterpret_cast<char*>(&b1), 1));
            bool r2 = static_cast<bool>(decoded.read(reinterpret_cast<char*>(&b2), 1));

            if (r1 != r2) {
                cerr << "Datoteke niso enake velikosti\n";
                goto nadaljuj;
            }

            if (!r1 && !r2) {
                cout << "Prisli smo do konca " << itteration << "\n";
                output << "File stevilka " << itteration << ":" << steviloRazlicnihBitov << "/" << bytePosition << "\n";
                vsota_vseh_skupnih_napak += steviloRazlicnihBitov;
                goto nadaljuj;
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


    }
    konec:
    output << "Povprecna napka: " << static_cast<double>(vsota_vseh_skupnih_napak)/stevilo_datotek << "\n";

    return 1;
}
