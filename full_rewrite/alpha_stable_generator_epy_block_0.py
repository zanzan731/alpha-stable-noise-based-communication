"""
GNU Radio Embedded Python Block: alpha_encoder

Kodira vhodne bajte v serijo vzorcev alfa-stabilne porazdelitve.
"""

import numpy as np
from gnuradio import gr
import sys



class alpha_encoder(gr.basic_block):
    """Kodira bajte v serijo vzorcev alfa-stabilne porazdelitve."""

    def __init__(
        self, 
        alpha_map=[1.2, 1.4, 1.6, 1.8], 
        beta_map=[-1.0, 1.0],
        gama_map=[0.5, 1.0, 1.5, 2.0],
        samples_per_symbol=500,
        encode_alpha=False,
        encode_beta=True,
        encode_gama=False,
    ):
        gr.basic_block.__init__(
            self,
            name="alpha_encoder",
            in_sig=[np.uint8],
            out_sig=[np.float32],
        )

        self.alpha_map = list(alpha_map)
        self.beta_map = list(beta_map)
        self.gama_map = list(gama_map)
        self.samples_per_symbol = int(samples_per_symbol)
        self.encode_alpha = bool(encode_alpha)
        self.encode_beta = bool(encode_beta)
        self.encode_gama = bool(encode_gama)

        self._bit_buffer = [] #mogoče vržemo potem ven
        #ta buffer bo ostal ker ima ful smisla da ostane boj input če ga preberem morem prebrat cel byte, če ne shranim moji padatki izginejo to je najbolj simple način kako se tega rešiti

        self._eos_reached = False #zato da lahko se samo ustavi
        self._ever_received_input = False #če tega ni bi lahko scheduler klical general_work preden dobi karkoli in konča predčasno
        self._consecutive_empty_calls = 0 #recimo temu nek stevc ki mi pove ali sm res koncal fora je da tezko ves ce ne poznas flowa celega grafa to mi pa pomaga določit ce zadosti časa nič ne dobim ali je res koncalo ali ne
        #basicly en empty_call ni zadosti da bi vedel ali je končalo ali ne žal flow graph ne deluje tako
        self._eos_confirm_calls = 1000 #to je meja koliko empty streamov rabim preden rečem da je _eos_reached = True, problem je da to ni popolna rešitev ampak trenutno nimam boljše ideje, če ne dela nastavi na več zna biti odvisna od flow grapha tako da mogoče bom nastavil kot parameter

        if self.samples_per_symbol <= 0:
            raise ValueError("samples_per_symbol must be pozitive number")
        if self.encode_alpha and not self.is_power_of_two(len(self.alpha_map)):
            raise ValueError("The size of alpha_map must be 2^n")
        if self.encode_beta and not self.is_power_of_two(len(self.beta_map)):
            raise ValueError("The size of beta_map must be 2^n")
        if self.encode_gama and not self.is_power_of_two(len(self.gama_map)):
            raise ValueError("The size of gama_map must be 2^n")

        self.bits_alpha = self.log2_za_potence2(len(self.alpha_map)) if self.encode_alpha else 0
        self.bits_beta  = self.log2_za_potence2(len(self.beta_map))  if self.encode_beta  else 0
        self.bits_gama  = self.log2_za_potence2(len(self.gama_map))  if self.encode_gama  else 0
        self.bits_per_symbol = self.bits_alpha + self.bits_beta + self.bits_gama # log(map_size) nam pove koliko bitov lahko predstavimo z vsakim parametrom, če to seštejemo imamo število bitov glede na semple

        if self.bits_per_symbol <= 0:
            raise ValueError("At least one of encode_alpha, encode_beta, encode_gama nust be True")

    def forecast(self, noutput_items, ninputs):
        return [0] * int(ninputs)

    @staticmethod
    def is_power_of_two(x):
        return x > 0 and (x & (x - 1)) == 0

    @staticmethod
    def log2_za_potence2(x):
        if x == 0:
            return 0
        if alpha_encoder.is_power_of_two(x):
            vrednost = 0
            while x > 1:
                x >>= 1
                vrednost += 1
            return vrednost
        raise ValueError("One of the mups is not the size of 2^n (something went wrong, this mesage should not be reachable)")

    @staticmethod
    def alpha_stable(size, alpha=1.1, beta=0.0, gama=1.0): #default walues that should be the best, encoding
        v_values = np.random.uniform(-np.pi / 2, np.pi / 2, size)
        w_values = np.random.exponential(1, size)

        constant = beta * np.tan(np.pi * alpha / 2)
        shift = np.arctan(constant)
        scale = (1 + constant ** 2) ** (1 / (2 * alpha))

        samples = (
            scale
            * np.sin(alpha * v_values + shift)
            / (np.cos(v_values)) ** (1 / alpha)
            * (np.cos((1 - alpha) * v_values - shift) / w_values) ** ((1 - alpha) / alpha)
        )
        return gama * samples

    @staticmethod
    def _read_bits(bit_buffer, start, count):
        #Kadar enkodiram za en simbol morem vedet kolko bitov lahko ta simbol enkoda (count parameter)
        #pazi ker vrne niz kjer je prvi prebran bit least significant, torej obrne (načeloma je vseeno samo rabiš upoštevat pri kodiranju da daš tud obrnt mapo)
        value = 0
        for index in range(count):
            value |= (bit_buffer[start + index] << index)
        return value

    #iz inputa preberi vse BYTE in vrni v bit_buffer 
    def _append_input_bits(self, input_bytes):
        for byte in input_bytes:
            byte_value = int(byte)
            for bit_index in range(8):
                self._bit_buffer.append((byte_value >> bit_index) & 1) #dubi samo zadnji bit zato &1  uno pa premakne na pravo mesto binary shift ku v c++

    def _encode_one_symbol(self, bit_offset):
        alpha = 1.1
        beta = 0.0
        gama = 1.0
        offset = bit_offset

        if self.encode_alpha:
            alpha_index = self._read_bits(self._bit_buffer, offset, self.bits_alpha)
            alpha = self.alpha_map[alpha_index]
            offset += self.bits_alpha

        if self.encode_beta:
            beta_index = self._read_bits(self._bit_buffer, offset, self.bits_beta)
            beta = self.beta_map[beta_index]
            offset += self.bits_beta

        if self.encode_gama:
            gama_index = self._read_bits(self._bit_buffer, offset, self.bits_gama)
            gama = self.gama_map[gama_index]
            offset += self.bits_gama

        return alpha, beta, gama

    def general_work(self, input_items, output_items):
        input_bytes = input_items[0]
        output_samples = output_items[0]

        '''
        if not hasattr(self, '_dbg_call'):
            self._dbg_call = 0
        self._dbg_call += 1 # da vem kolkokrat pokličem ta blok general_work
        c = self._dbg_call
        print(f"[ENC #{c}] id={id(self)} in={len(input_bytes)} out_buf={len(output_samples)} bit_buf={len(self._bit_buffer)} eos={self._eos_reached} ever={self._ever_received_input} empty_streak={self._consecutive_empty_calls}", file=sys.stderr, flush=True) 
        ''' #debuging

        if len(input_bytes) > 0:
            self._ever_received_input = True
            self._consecutive_empty_calls = 0 #nastavi nazaj na 0 da mi ne konča preveč hitro to je nujno če ne želim da mi prehit konča
            self._eos_reached = False
            self._append_input_bits(input_bytes) #direktno preberi dol iz inputa za delo naprej
            self.consume(0, len(input_bytes)) # to je za GNU radio da mu povem kolko podatkov sem pobral dol z vhoda, v tem klicu general work ostaja input_samples enak stream se ne nadaljuje po tem ko sem v tem bloku to je pomembno ker drugače ne bi smel delati tako
        elif self._ever_received_input:
            self._consecutive_empty_calls += 1 #za končat blok
            if self._consecutive_empty_calls >= self._eos_confirm_calls: #če presežem mejo dej eos_reached
                self._eos_reached = True
        else:
            # Če nikoli še nisem dubu podatkov samo loopi dokler jih ne dobim
            return 0
        
        if self._eos_reached and 0 < len(self._bit_buffer) < self.bits_per_symbol:
            # Zadnji delni simbol dopolnimo z ničlami, da ga še lahko zakodiramo, drugače lahko imamo v bit_bufferju ostanek če vhod ni deljiv z bits_per_symbol
            self._bit_buffer.extend([0] * (self.bits_per_symbol - len(self._bit_buffer)))
        
        # Encode as many symbols as we can fit in the output buffer
        max_symbols = len(output_samples) // self.samples_per_symbol #buffer ima v GNU radio omejeno velikost za output smiselno sicer ampak jaz bi šopal rad podatke čez
        produced_symbols = 0
        bit_offset = 0

        while (
            produced_symbols < max_symbols #če gremo čez bomo pisali v prazno in zgubili podatke, ne prekoračit bufferja
            and len(self._bit_buffer) - bit_offset >= self.bits_per_symbol #v bit_bufferju rabim zadosti simbolov da encodam celotno 
        ):
            alpha, beta, gama = self._encode_one_symbol(bit_offset)
            samples = self.alpha_stable(
                self.samples_per_symbol, alpha=alpha, beta=beta, gama=gama
            ).astype(np.float32)

            start = produced_symbols * self.samples_per_symbol
            end = start + self.samples_per_symbol
            output_samples[start:end] = samples

            produced_symbols += 1
            bit_offset += self.bits_per_symbol

        if bit_offset > 0:
            self._bit_buffer = self._bit_buffer[bit_offset:] #zamakni seznam vrži stran vse kar sem že predelal

        #print(f"[ENC #{c}] produced={produced_symbols} samples={produced_symbols*self.samples_per_symbol} bit_buf_after={len(self._bit_buffer)}", file=sys.stderr, flush=True)

        if produced_symbols > 0:
            return produced_symbols * self.samples_per_symbol

        if self._eos_reached and len(self._bit_buffer) < self.bits_per_symbol:
            #print(f"[ENC #{c}] WORK_DONE", file=sys.stderr, flush=True)
            return gr.WORK_DONE #to je GNU radio način da pove da je blok končal delo

        return 0