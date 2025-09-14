

## 15.3 Dynamic (Hardware-based) Relocation — Tái định vị động (dựa trên phần cứng)

Để hiểu cơ chế dịch địa chỉ (address translation) dựa trên phần cứng, trước tiên chúng ta sẽ xem xét phiên bản đầu tiên của nó. Ý tưởng này xuất hiện trong các máy tính time-sharing (chia sẻ thời gian) đầu tiên vào cuối những năm 1950, được gọi là **base and bounds** (cơ chế thanh ghi cơ sở và giới hạn). Kỹ thuật này cũng được gọi là **dynamic relocation** (tái định vị động); trong chương này, chúng ta sẽ sử dụng hai thuật ngữ này thay thế cho nhau [SS74].

Cụ thể, mỗi CPU sẽ cần hai thanh ghi phần cứng: một gọi là **base register** (thanh ghi cơ sở) và một gọi là **bounds register** (thanh ghi giới hạn, đôi khi gọi là limit register). Cặp base–bounds này cho phép chúng ta đặt **address space** (không gian địa chỉ) của process (tiến trình) ở bất kỳ vị trí nào trong **physical memory** (bộ nhớ vật lý), đồng thời đảm bảo process chỉ có thể truy cập vào không gian địa chỉ của chính nó.

> **ASIDE: SOFTWARE-BASED RELOCATION**  
> Trong giai đoạn đầu, trước khi có hỗ trợ phần cứng, một số hệ thống thực hiện tái định vị (relocation) ở dạng đơn giản hoàn toàn bằng phần mềm. Kỹ thuật cơ bản này được gọi là **static relocation** (tái định vị tĩnh), trong đó một phần mềm gọi là **loader** sẽ lấy một file thực thi (executable) sắp chạy và ghi lại (rewrite) các địa chỉ của nó sang một vị trí offset mong muốn trong physical memory.  
>  
> Ví dụ: nếu một lệnh là tải dữ liệu từ địa chỉ 1000 vào một thanh ghi (ví dụ: `movl 1000, %eax`), và không gian địa chỉ của chương trình được nạp bắt đầu tại địa chỉ 3000 (thay vì 0 như chương trình nghĩ), loader sẽ ghi lại lệnh này để cộng thêm offset 3000 vào mỗi địa chỉ (ví dụ: `movl 4000, %eax`). Bằng cách này, việc tái định vị tĩnh của không gian địa chỉ process được thực hiện.  
>  
> Tuy nhiên, static relocation có nhiều vấn đề. Quan trọng nhất là nó **không cung cấp bảo vệ** (protection), vì process có thể tạo ra các địa chỉ sai và truy cập trái phép vào bộ nhớ của process khác hoặc thậm chí bộ nhớ của OS. Nói chung, cần có hỗ trợ phần cứng để đạt được bảo vệ thực sự [WL+93]. Một nhược điểm khác là khi đã đặt xong, rất khó để di chuyển không gian địa chỉ sang vị trí khác [M65].

Trong cơ chế này, mỗi chương trình được viết và biên dịch như thể nó được nạp tại địa chỉ 0. Tuy nhiên, khi chương trình bắt đầu chạy, OS sẽ quyết định vị trí trong physical memory để nạp nó và thiết lập base register bằng giá trị đó. Trong ví dụ ở trên, OS quyết định nạp process tại địa chỉ vật lý 32 KB và đặt base register bằng giá trị này.

Khi process chạy, điều thú vị bắt đầu xảy ra. Mỗi khi process tạo ra một tham chiếu bộ nhớ, CPU sẽ dịch địa chỉ theo công thức:

```
physical address = virtual address + base
```

Mỗi tham chiếu bộ nhớ do process tạo ra là một **virtual address** (địa chỉ ảo); phần cứng sẽ cộng giá trị trong base register vào địa chỉ này để tạo ra **physical address** (địa chỉ vật lý) và gửi tới hệ thống bộ nhớ.

Để hiểu rõ hơn, hãy theo dõi quá trình thực thi một lệnh. Cụ thể, xét lệnh sau từ ví dụ trước:

```
128: movl 0x0(%ebx), %eax
```

**Program Counter (PC)** đang ở giá trị 128; khi phần cứng cần nạp lệnh này, nó sẽ cộng giá trị PC với base register (32 KB = 32768) để được địa chỉ vật lý 32896; sau đó phần cứng nạp lệnh từ địa chỉ vật lý này. Tiếp theo, CPU bắt đầu thực thi lệnh. Tại một thời điểm, process sẽ thực hiện:

> **TIP: HARDWARE-BASED DYNAMIC RELOCATION**  
> Với dynamic relocation, chỉ cần một chút phần cứng là có thể tạo ra hiệu quả lớn. Base register được dùng để biến đổi virtual address (do chương trình tạo ra) thành physical address. Bounds register (hoặc limit register) đảm bảo các địa chỉ này nằm trong phạm vi hợp lệ của address space. Kết hợp lại, chúng cung cấp một cơ chế ảo hóa bộ nhớ đơn giản và hiệu quả.

Lệnh load từ virtual address 15 KB, CPU sẽ cộng giá trị này với base register (32 KB) để được physical address 47 KB và lấy dữ liệu mong muốn.

Việc biến đổi virtual address thành physical address chính là kỹ thuật **address translation** (dịch địa chỉ). Vì quá trình này diễn ra khi chương trình đang chạy (runtime) và chúng ta có thể di chuyển address space ngay cả khi process đã chạy, nên kỹ thuật này được gọi là **dynamic relocation** [M65].

Bạn có thể thắc mắc: bounds register ở đâu? Thực tế, bounds register được dùng để bảo vệ. CPU sẽ kiểm tra xem virtual address có nằm trong giới hạn hay không; trong ví dụ trên, bounds register sẽ được đặt là 16 KB. Nếu process tạo ra một virtual address lớn hơn hoặc bằng bounds, hoặc âm, CPU sẽ phát sinh **exception** và process có thể bị chấm dứt. Mục đích của bounds là đảm bảo tất cả địa chỉ do process tạo ra đều hợp lệ.

Cần lưu ý rằng base và bounds register là các cấu trúc phần cứng nằm trên chip (mỗi CPU một cặp). Bộ phận của CPU hỗ trợ dịch địa chỉ thường được gọi là **Memory Management Unit (MMU)**; khi phát triển các kỹ thuật quản lý bộ nhớ phức tạp hơn, chúng ta sẽ bổ sung thêm mạch vào MMU.

Một lưu ý nhỏ: bounds register có thể được định nghĩa theo hai cách. Cách thứ nhất (như ở trên) là lưu kích thước của address space, và phần cứng sẽ so sánh virtual address với giá trị này trước khi cộng base. Cách thứ hai là lưu địa chỉ vật lý của điểm kết thúc address space, và phần cứng sẽ cộng base trước rồi mới kiểm tra giới hạn. Cả hai cách là tương đương về mặt logic; để đơn giản, chúng ta thường giả định cách thứ nhất.

### Ví dụ dịch địa chỉ

Giả sử một process có address space kích thước 4 KB (rất nhỏ, chỉ để minh họa) được nạp tại địa chỉ vật lý 16 KB. Kết quả dịch địa chỉ sẽ như sau:

*(Bảng minh họa kết quả dịch địa chỉ — giữ nguyên như bản gốc)*

Như bạn thấy, chỉ cần cộng base address với virtual address (có thể coi như offset trong address space) là ra physical address. Chỉ khi virtual address quá lớn hoặc âm thì mới gây ra lỗi (fault) và phát sinh exception.


## 15.4 Hardware Support: A Summary — Tóm tắt hỗ trợ phần cứng

Tóm tắt lại, phần cứng cần hỗ trợ những gì (xem thêm *Figure 15.3*, trang 9):

- Như đã thảo luận trong chương về **CPU virtualization** (ảo hóa CPU), cần có hai chế độ CPU: **privileged mode** (kernel mode) — OS chạy ở chế độ này và có toàn quyền truy cập máy; và **user mode** — ứng dụng chạy ở chế độ này và bị giới hạn quyền. Một bit trong **processor status word** sẽ cho biết CPU đang ở chế độ nào; khi có sự kiện đặc biệt (ví dụ: system call, exception hoặc interrupt), CPU sẽ chuyển chế độ.

- Phần cứng phải cung cấp base và bounds register; mỗi CPU có một cặp, là một phần của MMU. Khi chương trình người dùng chạy, phần cứng sẽ dịch mỗi địa chỉ bằng cách cộng base với virtual address do chương trình tạo ra. Đồng thời, phần cứng phải kiểm tra tính hợp lệ của địa chỉ bằng bounds register và mạch logic trong CPU.

- Phần cứng cần cung cấp các lệnh đặc biệt để thay đổi base và bounds register, cho phép OS thay đổi chúng khi chuyển đổi process. Các lệnh này là **privileged instructions** (lệnh đặc quyền); chỉ ở kernel mode mới có thể thay đổi. Hãy tưởng tượng mức độ hỗn loạn mà một process có thể gây ra[^1] nếu nó có thể tùy ý thay đổi base register khi đang chạy. Nghĩ thôi cũng đủ thấy đây là cơn ác mộng.

[^1]: Is there anything other than “havoc” that can be “wreaked”? [W17]

> **ASIDE: DATA STRUCTURE — THE FREE LIST**  
> Hệ điều hành (OS) phải theo dõi những phần bộ nhớ trống (free memory) chưa được sử dụng, để có thể cấp phát bộ nhớ cho các process (tiến trình). Có thể sử dụng nhiều cấu trúc dữ liệu khác nhau cho nhiệm vụ này; cấu trúc đơn giản nhất (mà chúng ta giả định ở đây) là **free list** (danh sách vùng trống), đơn giản chỉ là một danh sách các khoảng (range) của physical memory (bộ nhớ vật lý) hiện chưa được sử dụng.

**Figure 15.3: Dynamic Relocation — Hardware Requirements**  
*(Yêu cầu phần cứng cho tái định vị động)*

Cuối cùng, CPU phải có khả năng tạo ra **exception** (ngoại lệ) trong các tình huống khi một chương trình người dùng cố gắng truy cập bộ nhớ trái phép (với một địa chỉ “out of bounds” — vượt ngoài giới hạn). Trong trường hợp này, CPU sẽ dừng việc thực thi chương trình người dùng và chuyển quyền điều khiển cho **out-of-bounds exception handler** (trình xử lý ngoại lệ vượt giới hạn) của OS. Trình xử lý này sẽ quyết định cách phản ứng, thường là chấm dứt process vi phạm.  
Tương tự, nếu một chương trình người dùng cố gắng thay đổi giá trị của các thanh ghi đặc quyền (privileged) như base register và bounds register, CPU sẽ phát sinh exception và gọi **handler** xử lý tình huống “cố gắng thực hiện một thao tác đặc quyền khi đang ở user mode”. CPU cũng phải cung cấp một cơ chế để OS thông báo vị trí của các handler này; do đó cần thêm một số lệnh đặc quyền.


## 15.5 Operating System Issues — Các vấn đề của Hệ điều hành

Cũng giống như phần cứng cung cấp các tính năng mới để hỗ trợ **dynamic relocation** (tái định vị động), OS cũng phải xử lý các vấn đề mới; sự kết hợp giữa hỗ trợ phần cứng và quản lý của OS dẫn đến việc triển khai một dạng **virtual memory** (bộ nhớ ảo) đơn giản. Cụ thể, có một số thời điểm quan trọng mà OS phải can thiệp để thực hiện cơ chế virtual memory dựa trên base-and-bounds.

**Thứ nhất**, OS phải hành động khi một process được tạo, tìm chỗ trống trong bộ nhớ để đặt address space của nó. Với giả định rằng mỗi address space (a) nhỏ hơn kích thước physical memory và (b) có cùng kích thước, việc này khá đơn giản: OS có thể coi physical memory như một mảng các slot (ô nhớ) và theo dõi trạng thái từng slot (trống hay đã dùng). Khi một process mới được tạo, OS sẽ tìm trong cấu trúc dữ liệu (thường gọi là free list) để tìm chỗ trống cho address space mới và đánh dấu là đã sử dụng. Nếu address space có kích thước thay đổi, việc quản lý sẽ phức tạp hơn — vấn đề này sẽ được bàn ở các chương sau.

**Figure 15.4: Dynamic Relocation — Operating System Responsibilities**  
*(Trách nhiệm của hệ điều hành trong tái định vị động)*

Ví dụ: Trong Figure 15.2 (trang 5), OS sử dụng slot đầu tiên của physical memory cho chính nó, và đã tái định vị process từ ví dụ trước vào slot bắt đầu tại địa chỉ vật lý 32 KB. Hai slot còn lại (16 KB–32 KB và 48 KB–64 KB) đang trống; do đó free list sẽ gồm hai mục này.

**Thứ hai**, OS phải thu hồi bộ nhớ khi một process kết thúc (thoát bình thường hoặc bị buộc dừng do vi phạm). Khi process kết thúc, OS sẽ đưa vùng nhớ của nó trở lại free list và dọn dẹp các cấu trúc dữ liệu liên quan.

**Thứ ba**, OS phải thực hiện thêm một số bước khi xảy ra **context switch** (chuyển ngữ cảnh). Mỗi CPU chỉ có một cặp base–bounds register, và giá trị của chúng khác nhau cho mỗi process (vì mỗi process được nạp ở địa chỉ vật lý khác nhau). Do đó, OS phải lưu và khôi phục cặp thanh ghi này khi chuyển đổi giữa các process. Cụ thể, khi OS dừng một process, nó phải lưu giá trị base và bounds register vào bộ nhớ, trong một cấu trúc dữ liệu riêng cho process như **process structure** hoặc **process control block (PCB)**. Khi OS chạy lại process (hoặc chạy lần đầu), nó phải thiết lập base và bounds register trên CPU với giá trị đúng của process đó.

Cần lưu ý: khi một process bị dừng (không chạy), OS có thể di chuyển address space của nó sang vị trí khác trong bộ nhớ khá dễ dàng. Để làm điều này, OS sẽ **deschedule** process, sao chép address space từ vị trí hiện tại sang vị trí mới, sau đó cập nhật giá trị base register đã lưu (trong process structure) để trỏ tới vị trí mới. Khi process chạy lại, base register mới được khôi phục và process tiếp tục chạy mà không hề biết rằng mã lệnh và dữ liệu của mình đã ở vị trí khác trong bộ nhớ.

**Thứ tư**, OS phải cung cấp các **exception handler** (trình xử lý ngoại lệ) như đã đề cập; OS cài đặt các handler này khi khởi động (boot time) thông qua các lệnh đặc quyền. Ví dụ, nếu một process cố truy cập bộ nhớ ngoài giới hạn, CPU sẽ phát sinh exception; OS phải sẵn sàng xử lý, thường là chấm dứt process vi phạm. OS cần bảo vệ nghiêm ngặt hệ thống, và sẽ không “nhẹ tay” với process cố truy cập bộ nhớ hoặc thực thi lệnh trái phép.

**Figure 15.5: Limited Direct Execution (Dynamic Relocation) @ Boot**  
*(Thực thi trực tiếp có giới hạn — tái định vị động khi khởi động)*

Các Figure 15.5 và 15.6 (trang 12) minh họa tương tác phần cứng/OS theo dòng thời gian. Figure đầu cho thấy OS làm gì khi khởi động để chuẩn bị hệ thống; Figure thứ hai cho thấy khi một process (Process A) bắt đầu chạy, việc dịch địa chỉ được phần cứng xử lý hoàn toàn, không cần OS can thiệp. Tại một thời điểm, một **timer interrupt** xảy ra, OS chuyển sang Process B, process này thực hiện một “bad load” (truy cập địa chỉ bộ nhớ trái phép); lúc này OS phải can thiệp, chấm dứt process, giải phóng bộ nhớ và xóa entry của nó khỏi **process table**. Như bạn thấy, chúng ta vẫn theo mô hình **limited direct execution**: hầu hết thời gian, OS chỉ cần thiết lập phần cứng và để process chạy trực tiếp trên CPU; chỉ khi process vi phạm thì OS mới can thiệp.


## 15.6 Summary — Tóm tắt

Trong chương này, chúng ta đã mở rộng khái niệm **limited direct execution** với một cơ chế cụ thể dùng trong virtual memory, gọi là **address translation** (dịch địa chỉ). Với address translation, OS có thể kiểm soát mọi truy cập bộ nhớ của process, đảm bảo chúng nằm trong giới hạn của address space. Yếu tố then chốt để kỹ thuật này hiệu quả là hỗ trợ phần cứng, giúp dịch địa chỉ nhanh chóng cho mỗi lần truy cập, biến virtual address (cách process nhìn bộ nhớ) thành physical address (cách bộ nhớ thực tế được tổ chức). Tất cả diễn ra hoàn toàn **transparent** (minh bạch) với process — nó không hề biết rằng các truy cập bộ nhớ đang được dịch.

**Figure 15.6: Limited Direct Execution (Dynamic Relocation) @ Runtime**  
*(Thực thi trực tiếp có giới hạn — tái định vị động khi chạy)*

Chúng ta cũng đã thấy một dạng ảo hóa cụ thể, gọi là **base and bounds** hoặc **dynamic relocation**. Cơ chế này rất hiệu quả vì chỉ cần thêm một chút logic phần cứng để cộng base register vào virtual address và kiểm tra địa chỉ có nằm trong bounds hay không. Nó cũng cung cấp **protection** (bảo vệ): OS và phần cứng phối hợp để đảm bảo không process nào có thể tạo ra truy cập bộ nhớ ngoài address space của chính nó. Bảo vệ là một trong những mục tiêu quan trọng nhất của OS; nếu không có nó, OS không thể kiểm soát hệ thống (process có thể ghi đè vùng nhớ quan trọng như trap table và chiếm quyền điều khiển).

Tuy nhiên, kỹ thuật dynamic relocation đơn giản này vẫn có nhược điểm. Ví dụ, như trong Figure 15.2 (trang 5), process được tái định vị sử dụng physical memory từ 32 KB đến 48 KB; nhưng vì stack và heap của process không lớn, phần bộ nhớ giữa chúng bị bỏ trống. Kiểu lãng phí này gọi là **internal fragmentation** (phân mảnh bên trong), khi không gian bên trong đơn vị cấp phát không được sử dụng hết và bị bỏ phí. Trong cách tiếp cận hiện tại, dù có