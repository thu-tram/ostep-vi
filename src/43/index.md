# 43. Hệ thống tệp cấu trúc nhật ký (Log-structured File Systems)

Vào đầu những năm 1990, một nhóm nghiên cứu tại Berkeley do Giáo sư John Ousterhout và nghiên cứu sinh Mendel Rosenblum dẫn dắt đã phát triển một hệ thống tệp mới được gọi là **log-structured file system** (LFS) [RO91]. Động lực để họ thực hiện điều này dựa trên các quan sát sau:

* **Bộ nhớ hệ thống ngày càng lớn:** Khi dung lượng bộ nhớ tăng, nhiều dữ liệu hơn có thể được lưu trong bộ nhớ đệm (cache). Khi nhiều dữ liệu được cache hơn, lưu lượng truy cập đĩa ngày càng bao gồm nhiều thao tác ghi, vì các thao tác đọc được phục vụ trực tiếp từ cache. Do đó, hiệu năng của file system phần lớn được quyết định bởi hiệu năng ghi.
* **Tồn tại khoảng cách lớn giữa hiệu năng I/O ngẫu nhiên và I/O tuần tự:** Băng thông truyền dữ liệu của ổ cứng đã tăng đáng kể qua các năm [P98]; khi nhiều bit hơn được ghi trên bề mặt đĩa, băng thông khi truy cập các bit đó cũng tăng. Tuy nhiên, chi phí tìm kiếm (seek) và độ trễ quay (rotational delay) lại giảm chậm; việc chế tạo các động cơ nhỏ, giá rẻ để quay đĩa nhanh hơn hoặc di chuyển tay đọc nhanh hơn là một thách thức. Vì vậy, nếu có thể sử dụng đĩa theo cách tuần tự, bạn sẽ đạt được lợi thế hiệu năng đáng kể so với các phương pháp gây ra nhiều thao tác seek và quay.
* **Các file system hiện tại hoạt động kém trên nhiều loại workload phổ biến:** Ví dụ, **FFS** [MJLF84] sẽ thực hiện một số lượng lớn thao tác ghi chỉ để tạo một file mới có kích thước một block: một lần ghi cho inode mới, một lần để cập nhật inode bitmap, một lần cho data block của thư mục chứa file, một lần cho inode của thư mục để cập nhật nó, một lần cho data block mới của file, và một lần cho data bitmap để đánh dấu block dữ liệu đã được cấp phát. Mặc dù FFS đặt tất cả các block này trong cùng một block group, nó vẫn phải thực hiện nhiều thao tác seek ngắn và các lần trễ quay tiếp theo, khiến hiệu năng thấp hơn nhiều so với băng thông tuần tự tối đa.
* **File system không nhận thức về RAID:** Ví dụ, cả RAID-4 và RAID-5 đều gặp vấn đề **small-write** (ghi nhỏ), trong đó một thao tác ghi logic vào một block duy nhất sẽ gây ra 4 thao tác I/O vật lý. Các file system hiện tại không cố gắng tránh hành vi ghi tệ nhất này trên RAID.

>> **TIP: CHI TIẾT LÀ QUAN TRỌNG**  
>> Tất cả các hệ thống thú vị đều bao gồm một vài ý tưởng tổng quát và nhiều chi tiết. Đôi khi, khi học về các hệ thống này, bạn có thể nghĩ: “Ồ, tôi hiểu ý tưởng chung rồi; phần còn lại chỉ là chi tiết,” và từ đó chỉ học một nửa cách hệ thống thực sự hoạt động. Đừng làm vậy! Nhiều khi, chính các chi tiết mới là yếu tố then chốt. Như chúng ta sẽ thấy với LFS, ý tưởng tổng thể rất dễ hiểu, nhưng để xây dựng một hệ thống hoạt động thực sự, bạn phải suy nghĩ kỹ về tất cả các trường hợp phức tạp.

Một file system lý tưởng sẽ tập trung vào hiệu năng ghi, và cố gắng tận dụng băng thông tuần tự của đĩa. Hơn nữa, nó sẽ hoạt động tốt với các workload phổ biến không chỉ ghi dữ liệu mà còn thường xuyên cập nhật các cấu trúc metadata trên đĩa. Cuối cùng, nó sẽ hoạt động tốt cả trên RAID lẫn ổ đĩa đơn.

Loại file system mới mà Rosenblum và Ousterhout giới thiệu được gọi là **LFS** (Log-structured File System). Khi ghi xuống đĩa, LFS trước tiên sẽ **buffer** (đệm) tất cả các bản cập nhật (bao gồm cả metadata!) trong một **segment** (phân đoạn) nằm trong bộ nhớ; khi segment đầy, nó sẽ được ghi xuống đĩa trong một lần truyền tuần tự dài tới một vùng chưa sử dụng của đĩa. LFS **không bao giờ** ghi đè dữ liệu hiện có, mà luôn ghi các segment vào các vị trí trống. Vì các segment có kích thước lớn, đĩa (hoặc RAID) được sử dụng hiệu quả, và hiệu năng của file system đạt gần mức tối đa.

>> **THE CRUX: LÀM THẾ NÀO ĐỂ BIẾN MỌI GHI THÀNH GHI TUẦN TỰ?**  
>> Làm thế nào một file system có thể biến tất cả các thao tác ghi thành ghi tuần tự? Đối với thao tác đọc, điều này là không thể, vì block cần đọc có thể nằm ở bất kỳ đâu trên đĩa. Tuy nhiên, đối với thao tác ghi, file system **luôn có quyền lựa chọn**, và chính lựa chọn này là điều chúng ta muốn khai thác.

## 43.1 Ghi tuần tự xuống đĩa (Writing To Disk Sequentially)

Như vậy, chúng ta có thách thức đầu tiên: làm thế nào để biến tất cả các bản cập nhật trạng thái của file system (hệ thống tệp) thành một chuỗi các thao tác ghi tuần tự xuống đĩa? Để hiểu rõ hơn, hãy sử dụng một ví dụ đơn giản. Giả sử chúng ta đang ghi một **data block** (khối dữ liệu) D vào một file. Việc ghi data block này xuống đĩa có thể dẫn đến bố cục trên đĩa như sau, với D được ghi tại địa chỉ đĩa A0:

...

Tuy nhiên, khi người dùng ghi một data block, không chỉ dữ liệu được ghi xuống đĩa; còn có các **metadata** (siêu dữ liệu) khác cần được cập nhật. Trong trường hợp này, giả sử chúng ta cũng ghi **inode** (chỉ mục nút) I của file xuống đĩa, và inode này trỏ tới data block D. Khi được ghi xuống đĩa, data block và inode sẽ trông như sau (lưu ý rằng inode có vẻ lớn bằng data block, điều này thường không đúng; trong hầu hết các hệ thống, data block có kích thước 4 KB, trong khi inode nhỏ hơn nhiều, khoảng 128 byte):

...

Ý tưởng cơ bản này — đơn giản là ghi tất cả các bản cập nhật (như data block, inode, v.v.) xuống đĩa theo thứ tự tuần tự — chính là cốt lõi của LFS (Log-structured File System). Nếu bạn hiểu điều này, bạn đã nắm được ý tưởng chính. Nhưng như với mọi hệ thống phức tạp, “quỷ dữ nằm trong chi tiết” — các chi tiết mới là phần khó.


## 43.2 Ghi tuần tự và hiệu quả (Writing Sequentially And Effectively)

Thật không may, chỉ ghi tuần tự xuống đĩa **không** đủ để đảm bảo hiệu năng ghi cao. Ví dụ, giả sử chúng ta ghi một block duy nhất vào địa chỉ A tại thời điểm T. Sau đó, chúng ta chờ một lúc, rồi ghi xuống đĩa tại địa chỉ A + 1 (địa chỉ block tiếp theo theo thứ tự tuần tự), nhưng ở thời điểm T + δ. Trong khoảng thời gian giữa lần ghi thứ nhất và thứ hai, đĩa đã quay; khi bạn phát lệnh ghi thứ hai, nó sẽ phải chờ gần như cả một vòng quay trước khi được ghi (cụ thể, nếu thời gian quay là $T_{rotation}$, thì đĩa sẽ phải chờ $T_{rotation} - δ$ trước khi có thể ghi block thứ hai xuống bề mặt đĩa).  

Do đó, bạn có thể thấy rằng chỉ ghi xuống đĩa theo thứ tự tuần tự là chưa đủ để đạt hiệu năng tối đa; thay vào đó, bạn phải phát lệnh ghi một số lượng lớn các block liên tiếp (hoặc một thao tác ghi lớn duy nhất) để đạt hiệu năng ghi tốt.

Để đạt được điều này, LFS sử dụng một kỹ thuật lâu đời được gọi là **write buffering** (đệm ghi)^[1]. Trước khi ghi xuống đĩa, LFS lưu trữ các bản cập nhật trong bộ nhớ; khi đã nhận đủ số lượng bản cập nhật, nó sẽ ghi tất cả xuống đĩa cùng một lúc, đảm bảo sử dụng đĩa một cách hiệu quả.

[^1]: Thực tế rất khó tìm một tài liệu tham khảo “chuẩn” cho ý tưởng này, vì nó có thể đã được phát minh bởi nhiều người từ rất sớm trong lịch sử ngành máy tính. Để tìm hiểu lợi ích của write buffering, xem Solworth và Orji [SO90]; để tìm hiểu các tác hại tiềm ẩn, xem Mogul [M94].

Phần dữ liệu lớn mà LFS ghi trong một lần được gọi là **segment** (phân đoạn). Mặc dù thuật ngữ này bị lạm dụng trong nhiều lĩnh vực của hệ thống máy tính, ở đây nó chỉ đơn giản là một khối dữ liệu lớn mà LFS dùng để gom nhóm các thao tác ghi. Do đó, khi ghi xuống đĩa, LFS sẽ buffer các bản cập nhật trong một segment nằm trong bộ nhớ, rồi ghi toàn bộ segment này xuống đĩa trong một lần. Miễn là segment đủ lớn, các thao tác ghi này sẽ đạt hiệu quả cao.

Dưới đây là một ví dụ, trong đó LFS buffer hai nhóm bản cập nhật vào một segment nhỏ; các segment thực tế thường lớn hơn (vài MB). Bản cập nhật đầu tiên gồm bốn thao tác ghi block cho file **j**; bản cập nhật thứ hai là thêm một block vào file **k**. LFS sau đó commit toàn bộ segment gồm bảy block này xuống đĩa trong một lần. Bố cục trên đĩa của các block này sau khi ghi như sau:

...


## 43.3 Buffer bao nhiêu là đủ? (How Much To Buffer?)

Điều này dẫn đến câu hỏi: **LFS** (Log-structured File System) nên buffer (đệm) bao nhiêu bản cập nhật trước khi ghi xuống đĩa? Câu trả lời, tất nhiên, phụ thuộc vào chính ổ đĩa, cụ thể là mức **positioning overhead** (chi phí định vị – bao gồm thời gian quay và seek) so với **transfer rate** (tốc độ truyền dữ liệu); hãy xem lại chương về **FFS** để tham khảo một phân tích tương tự.

Ví dụ, giả sử thời gian định vị (tức là chi phí quay và seek) trước mỗi lần ghi mất khoảng \( T_{position} \) giây. Giả sử thêm rằng tốc độ truyền dữ liệu cực đại của đĩa là \( R_{peak} \) MB/s. Vậy LFS nên buffer bao nhiêu dữ liệu trước khi ghi khi chạy trên loại đĩa này?

Cách suy nghĩ ở đây là: mỗi lần ghi, bạn phải trả một chi phí cố định cho việc định vị. Vậy bạn cần ghi bao nhiêu dữ liệu để **amortize** (phân bổ) chi phí đó? Rõ ràng, càng ghi nhiều thì càng tốt, và bạn sẽ càng tiến gần đến việc đạt được băng thông cực đại.

Để có câu trả lời cụ thể, giả sử chúng ta ghi ra \( D \) MB dữ liệu. Thời gian để ghi khối dữ liệu này (\( T_{write} \)) sẽ bằng thời gian định vị \( T_{position} \) cộng với thời gian truyền \( D \) MB dữ liệu (\( \frac{D}{R_{peak}} \)), tức là:

[
T_{write} = T_{position} + \frac{D}{R_{peak}}
\]

Do đó, **tốc độ ghi hiệu dụng** (\( R_{effective} \)) — chính là lượng dữ liệu ghi được chia cho tổng thời gian ghi — sẽ là:

[
R_{effective} = \frac{D}{T_{position} + \frac{D}{R_{peak}}}
\]

Điều chúng ta quan tâm là làm cho \( R_{effective} \) tiến gần tới \( R_{peak} \). Cụ thể, chúng ta muốn tốc độ hiệu dụng bằng một phần \( F \) của tốc độ cực đại, với \( 0 < F < 1 \) (một giá trị F điển hình có thể là 0.9, tức 90% tốc độ cực đại). Về mặt toán học, điều này có nghĩa là:

[
R_{effective} = F \times R_{peak}
\]

Tại đây, chúng ta có thể giải ra \( D \):

[
D = \frac{F}{1 - F} \times R_{peak} \times T_{position}
\]

Hãy làm một ví dụ: với một ổ đĩa có thời gian định vị là 10 mili-giây và tốc độ truyền cực đại là 100 MB/s; giả sử chúng ta muốn băng thông hiệu dụng đạt 90% tốc độ cực đại (F = 0.9). Khi đó:

[
D = \frac{0.9}{0.1} \times 100 \ \text{MB/s} \times 0.01 \ \text{giây} = 9 \ \text{MB}
\]

Hãy thử một vài giá trị khác để xem cần buffer bao nhiêu để tiến gần tới băng thông cực đại. Cần bao nhiêu để đạt 95% tốc độ cực đại? 99%?


## 43.4 Vấn đề: Tìm inode (Problem: Finding Inodes)

Để hiểu cách tìm một **inode** trong LFS, trước hết hãy xem lại cách tìm inode trong một file system UNIX điển hình. Trong một file system thông thường như **FFS**, hoặc thậm chí là hệ thống tệp UNIX cũ, việc tìm inode rất dễ, vì chúng được tổ chức thành một mảng và đặt trên đĩa ở các vị trí cố định.

Ví dụ, hệ thống tệp UNIX cũ lưu tất cả inode ở một vùng cố định trên đĩa. Do đó, khi biết số inode (inode number) và địa chỉ bắt đầu, để tìm một inode cụ thể, bạn chỉ cần tính địa chỉ đĩa chính xác của nó bằng cách nhân số inode với kích thước của một inode, rồi cộng với địa chỉ bắt đầu của mảng inode trên đĩa; việc **array-based indexing** (đánh chỉ số dựa trên mảng) này, khi biết số inode, là nhanh và đơn giản.

Việc tìm inode khi biết số inode trong FFS chỉ phức tạp hơn một chút, vì FFS chia bảng inode thành các khối (chunk) và đặt một nhóm inode trong mỗi **cylinder group**. Do đó, bạn cần biết kích thước của mỗi khối inode và địa chỉ bắt đầu của từng khối. Sau đó, các phép tính tương tự và cũng dễ dàng.

Trong LFS, mọi thứ khó khăn hơn nhiều. Tại sao? Bởi vì chúng ta đã “rải” các inode khắp đĩa! Tệ hơn nữa, chúng ta **không bao giờ ghi đè tại chỗ** (overwrite in place), và do đó phiên bản mới nhất của một inode (tức là phiên bản mà chúng ta cần) liên tục thay đổi vị trí.

## 43.5 Giải pháp thông qua gián tiếp: Inode Map (Bản đồ inode)

Để khắc phục vấn đề này, các nhà thiết kế của **LFS** (Log-structured File System) đã giới thiệu một lớp **indirection** (gián tiếp) giữa **inode number** (số inode) và chính inode, thông qua một cấu trúc dữ liệu gọi là **inode map** (imap – bản đồ inode). **Imap** là một cấu trúc nhận vào số inode và trả về **địa chỉ đĩa** (disk address) của phiên bản inode mới nhất.

>> **TIP: SỬ DỤNG MỘT LỚP GIÁN TIẾP**  
>> Người ta thường nói rằng giải pháp cho mọi vấn đề trong Khoa học Máy tính chỉ đơn giản là thêm một lớp gián tiếp. Điều này rõ ràng không hoàn toàn đúng; nó chỉ là giải pháp cho **hầu hết** các vấn đề (vâng, nhận xét này vẫn hơi quá, nhưng bạn hiểu ý rồi đấy). Bạn hoàn toàn có thể coi mọi cơ chế ảo hóa (virtualization) mà chúng ta đã học, ví dụ như **virtual memory** (bộ nhớ ảo) hay khái niệm file, như là một lớp gián tiếp. Và chắc chắn **inode map** trong LFS là một dạng ảo hóa của inode number. Hy vọng bạn có thể thấy sức mạnh to lớn của gián tiếp trong các ví dụ này, cho phép chúng ta tự do di chuyển các cấu trúc (như page trong ví dụ VM, hoặc inode trong LFS) mà không cần thay đổi mọi tham chiếu tới chúng. Tất nhiên, gián tiếp cũng có mặt trái: chi phí bổ sung (overhead). Vì vậy, lần tới khi bạn gặp một vấn đề, hãy thử giải quyết nó bằng gián tiếp, nhưng nhớ cân nhắc kỹ chi phí của việc này. Như Wheeler đã nổi tiếng nói: “Mọi vấn đề trong khoa học máy tính đều có thể được giải quyết bằng một lớp gián tiếp khác, ngoại trừ vấn đề có quá nhiều lớp gián tiếp.”  

Vì vậy, bạn có thể hình dung imap thường được triển khai như một mảng đơn giản, với 4 byte (một con trỏ đĩa) cho mỗi phần tử. Mỗi khi một inode được ghi xuống đĩa, imap sẽ được cập nhật với vị trí mới của nó.

Tuy nhiên, imap cần được lưu trữ **persistent** (bền vững – tức là ghi xuống đĩa); làm như vậy cho phép LFS theo dõi vị trí của các inode ngay cả khi hệ thống bị crash, và do đó hoạt động như mong muốn. Vậy câu hỏi đặt ra: **imap nên được đặt ở đâu trên đĩa?**

Tất nhiên, nó có thể nằm ở một vị trí cố định trên đĩa. Nhưng thật không may, vì nó được cập nhật thường xuyên, điều này sẽ yêu cầu mỗi lần cập nhật cấu trúc file phải kèm theo một lần ghi imap, và do đó hiệu năng sẽ giảm (tức là sẽ có nhiều thao tác **disk seek** hơn, giữa mỗi lần cập nhật và vị trí cố định của imap).

Thay vào đó, LFS đặt các **chunk** (mảnh) của inode map ngay bên cạnh nơi nó đang ghi tất cả thông tin mới khác. Do đó, khi append (nối thêm) một data block vào file *k*, LFS thực tế sẽ ghi **data block mới**, **inode** của nó, và **một phần của inode map** cùng nhau xuống đĩa, như sau:

...

Trong hình minh họa này, phần của mảng imap được lưu trong block được đánh dấu “imap” cho LFS biết rằng inode *k* nằm ở địa chỉ đĩa A1; inode này, đến lượt nó, cho LFS biết rằng data block D của nó nằm ở địa chỉ A0.


## 43.6 Hoàn thiện giải pháp: Checkpoint Region (Vùng điểm kiểm)

Người đọc tinh ý (chính là bạn, đúng không?) có thể nhận ra một vấn đề ở đây: **Làm thế nào để tìm inode map, khi các phần của nó cũng đã được rải khắp đĩa?** Cuối cùng thì không có phép màu nào cả: file system phải có một vị trí cố định và đã biết trên đĩa để bắt đầu quá trình tìm kiếm file.

LFS có một vị trí cố định như vậy trên đĩa, được gọi là **checkpoint region** (CR – vùng điểm kiểm). Checkpoint region chứa các con trỏ (tức là địa chỉ) tới các phần mới nhất của inode map, và do đó có thể tìm thấy các phần của inode map bằng cách đọc CR trước. Lưu ý rằng checkpoint region chỉ được cập nhật định kỳ (ví dụ khoảng mỗi 30 giây), và do đó hiệu năng không bị ảnh hưởng đáng kể.  

Như vậy, cấu trúc tổng thể của bố cục trên đĩa sẽ bao gồm:  
- **Checkpoint region** (trỏ tới các phần mới nhất của inode map)  
- Các phần của inode map (mỗi phần chứa địa chỉ của các inode)  
- Các inode (trỏ tới file và thư mục) giống như trong các file system UNIX điển hình.

Dưới đây là một ví dụ về checkpoint region (lưu ý nó nằm ngay ở đầu đĩa, tại địa chỉ 0), cùng với một **imap chunk**, một inode, và một data block. Một file system thực tế tất nhiên sẽ có CR lớn hơn nhiều (thực tế là có **hai** CR, như chúng ta sẽ tìm hiểu sau), nhiều imap chunk, và tất nhiên là nhiều inode, data block, v.v.

...

## 43.7 Đọc một file từ đĩa: Tóm tắt (Reading A File From Disk: A Recap)

Để đảm bảo bạn hiểu cách **LFS** (Log-structured File System) hoạt động, chúng ta hãy cùng đi qua các bước cần thực hiện để đọc một file từ đĩa. Giả sử ban đầu chúng ta **không có gì trong bộ nhớ**. Cấu trúc dữ liệu đầu tiên trên đĩa mà chúng ta phải đọc là **checkpoint region** (vùng điểm kiểm). Checkpoint region chứa các con trỏ (tức là địa chỉ đĩa) tới toàn bộ **inode map** (imap – bản đồ inode), và do đó LFS sẽ đọc toàn bộ inode map này vào bộ nhớ và lưu trong cache.

Từ thời điểm này, khi được cung cấp **inode number** (số inode) của một file, LFS chỉ cần tra cứu ánh xạ từ inode number sang **inode disk address** (địa chỉ inode trên đĩa) trong imap, và đọc phiên bản inode mới nhất. Để đọc một block từ file, LFS sẽ tiến hành giống hệt như một file system UNIX điển hình, bằng cách sử dụng **direct pointer** (con trỏ trực tiếp), **indirect pointer** (con trỏ gián tiếp) hoặc **doubly-indirect pointer** (con trỏ gián tiếp kép) khi cần.  

Trong trường hợp thông thường, LFS sẽ thực hiện **số lượng thao tác I/O** tương đương với một file system điển hình khi đọc file từ đĩa; toàn bộ imap đã được cache, và công việc bổ sung duy nhất mà LFS thực hiện trong quá trình đọc là tra cứu địa chỉ inode trong imap.


## 43.8 Còn thư mục thì sao? (What About Directories?)

Cho đến giờ, chúng ta đã đơn giản hóa phần thảo luận bằng cách chỉ xét đến inode và data block. Tuy nhiên, để truy cập một file trong file system (ví dụ `/home/remzi/foo` – một trong những tên file giả ưa thích của chúng tôi), một số **directory** (thư mục) cũng phải được truy cập. Vậy LFS lưu trữ dữ liệu thư mục như thế nào?

May mắn thay, cấu trúc thư mục về cơ bản **giống hệt** như trong các file system UNIX cổ điển, ở chỗ một thư mục chỉ là một tập hợp các ánh xạ **(tên, inode number)**. Ví dụ, khi tạo một file trên đĩa, LFS phải ghi một inode mới, một số dữ liệu, cũng như dữ liệu thư mục và inode của thư mục tham chiếu đến file này. Hãy nhớ rằng LFS sẽ thực hiện việc này **tuần tự** trên đĩa (sau khi buffer các bản cập nhật trong một thời gian).  

Do đó, việc tạo một file `foo` trong một thư mục sẽ dẫn đến các cấu trúc mới trên đĩa như sau:

...

Phần của inode map sẽ chứa thông tin về vị trí của cả file thư mục `dir` và file mới tạo `f`. Do đó, khi truy cập file `foo` (có inode number `k`), bạn sẽ:  
1. Tra cứu trong inode map (thường được cache trong bộ nhớ) để tìm vị trí của inode của thư mục `dir` (A3).  
2. Đọc inode của thư mục, từ đó lấy vị trí của dữ liệu thư mục (A2).  
3. Đọc data block này để nhận được ánh xạ **(tên, inode number)** của (`foo`, `k`).  
4. Tra cứu lại inode map để tìm vị trí của inode number `k` (A1).  
5. Cuối cùng, đọc data block mong muốn tại địa chỉ A0.


Có một vấn đề nghiêm trọng khác trong LFS mà inode map giải quyết, được gọi là **recursive update problem** (vấn đề cập nhật đệ quy) [Z+12]. Vấn đề này xuất hiện trong bất kỳ file system nào **không bao giờ cập nhật tại chỗ** (never updates in place) như LFS, mà thay vào đó di chuyển các bản cập nhật tới vị trí mới trên đĩa.

Cụ thể, bất cứ khi nào một inode được cập nhật, vị trí của nó trên đĩa sẽ thay đổi. Nếu không cẩn thận, điều này sẽ kéo theo việc phải cập nhật cả thư mục trỏ tới file đó, rồi lại phải thay đổi thư mục cha của thư mục đó, và cứ thế lan lên toàn bộ cây thư mục của file system.

LFS đã khéo léo tránh được vấn đề này nhờ inode map. Mặc dù vị trí của một inode có thể thay đổi, nhưng sự thay đổi này **không bao giờ** được phản ánh vào chính thư mục; thay vào đó, cấu trúc imap được cập nhật, trong khi thư mục vẫn giữ nguyên ánh xạ **(tên, inode number)**. Nhờ cơ chế gián tiếp này, LFS tránh được vấn đề cập nhật đệ quy.


## 43.9 Một vấn đề mới: Thu gom rác (Garbage Collection)

Bạn có thể đã nhận thấy một vấn đề khác với **LFS** (Log-structured File System): nó liên tục ghi phiên bản mới nhất của một file (bao gồm cả inode và dữ liệu) vào các vị trí mới trên đĩa. Quá trình này, mặc dù giúp duy trì hiệu quả ghi, lại dẫn đến việc LFS để lại các phiên bản cũ của cấu trúc file rải rác khắp đĩa. Chúng ta (một cách không mấy trang trọng) gọi các phiên bản cũ này là **garbage** (rác).

Ví dụ, hãy tưởng tượng trường hợp chúng ta có một file hiện có được tham chiếu bởi **inode number** (số inode) *k*, trỏ tới một **data block** (khối dữ liệu) duy nhất D0. Giờ chúng ta cập nhật block đó, tạo ra cả một inode mới và một data block mới. Bố cục trên đĩa của LFS sau đó sẽ trông như sau (lưu ý chúng ta bỏ qua imap và các cấu trúc khác để đơn giản hóa; một **chunk** mới của imap cũng sẽ phải được ghi xuống đĩa để trỏ tới inode mới):

...

Trong sơ đồ, bạn có thể thấy cả inode và data block đều có hai phiên bản trên đĩa: một phiên bản cũ (bên trái) và một phiên bản hiện tại, tức là **live** (đang được sử dụng – bên phải). Chỉ với hành động (logic) cập nhật một data block, một số cấu trúc mới phải được LFS ghi bền vững xuống đĩa, để lại các phiên bản cũ của các block đó trên đĩa.

Một ví dụ khác: giả sử thay vì cập nhật, chúng ta **append** (nối thêm) một block vào file gốc *k*. Trong trường hợp này, một phiên bản inode mới được tạo ra, nhưng data block cũ vẫn được inode trỏ tới. Do đó, nó vẫn **live** và hoàn toàn là một phần của file system hiện tại:

...

Vậy chúng ta nên làm gì với các phiên bản cũ của inode, data block, và các cấu trúc khác? Một lựa chọn là giữ lại các phiên bản cũ này và cho phép người dùng khôi phục các phiên bản file trước đó (ví dụ, khi họ vô tình ghi đè hoặc xóa file, điều này có thể rất hữu ích); một file system như vậy được gọi là **versioning file system** vì nó lưu lại các phiên bản khác nhau của một file.

Tuy nhiên, LFS chỉ giữ lại phiên bản **live** mới nhất của một file; do đó (ở chế độ nền), LFS phải định kỳ tìm các phiên bản cũ không còn sử dụng của dữ liệu file, inode, và các cấu trúc khác, rồi **clean** (dọn dẹp) chúng; việc dọn dẹp này sẽ giải phóng các block trên đĩa để sử dụng cho các lần ghi tiếp theo. Lưu ý rằng quá trình cleaning là một dạng **garbage collection** (thu gom rác), một kỹ thuật xuất hiện trong các ngôn ngữ lập trình có khả năng tự động giải phóng bộ nhớ không còn được sử dụng.

Trước đây, chúng ta đã thảo luận về **segment** (phân đoạn) như một cơ chế quan trọng giúp LFS thực hiện các thao tác ghi lớn xuống đĩa. Hóa ra, segment cũng đóng vai trò then chốt trong việc cleaning hiệu quả. Hãy tưởng tượng điều gì sẽ xảy ra nếu **LFS cleaner** chỉ đơn giản đi qua và giải phóng từng data block, inode, v.v., riêng lẻ trong quá trình cleaning. Kết quả: một file system với một số lượng lỗ trống (free hole) xen kẽ giữa các vùng đã cấp phát trên đĩa. Hiệu năng ghi sẽ giảm đáng kể, vì LFS sẽ không thể tìm được một vùng liên tục đủ lớn để ghi tuần tự xuống đĩa với hiệu năng cao.

Thay vào đó, LFS cleaner hoạt động theo **từng segment**, nhờ đó giải phóng các vùng lớn cho các lần ghi tiếp theo. Quá trình cleaning cơ bản diễn ra như sau: định kỳ, LFS cleaner đọc một số segment cũ (đang được sử dụng một phần), xác định block nào **live** trong các segment này, sau đó ghi ra một tập hợp segment mới chỉ chứa các block live, giải phóng các segment cũ để ghi mới. Cụ thể, chúng ta kỳ vọng cleaner sẽ đọc vào **M** segment hiện có, nén (compact) nội dung của chúng thành **N** segment mới (với N < M), rồi ghi N segment này xuống đĩa ở các vị trí mới. M segment cũ sau đó được giải phóng và có thể được file system sử dụng cho các lần ghi tiếp theo.

Tuy nhiên, bây giờ chúng ta còn lại hai vấn đề:  
1. **Cơ chế (mechanism):** Làm thế nào để LFS biết block nào trong một segment là live, và block nào là dead?  
2. **Chính sách (policy):** Cleaner nên chạy thường xuyên như thế nào, và nên chọn segment nào để dọn?


## 43.10 Xác định trạng thái sống của block (Determining Block Liveness)

Chúng ta sẽ giải quyết vấn đề **cơ chế** trước. Với một **data block** D nằm trong một **on-disk segment** S, LFS phải có khả năng xác định liệu D có **live** hay không. Để làm điều này, LFS thêm một lượng nhỏ thông tin bổ sung vào mỗi segment để mô tả từng block. Cụ thể, LFS lưu kèm với mỗi data block D: **inode number** (số inode – cho biết block này thuộc file nào) và **offset** (chỉ số block trong file). Thông tin này được ghi trong một cấu trúc ở đầu segment, gọi là **segment summary block**.

Với thông tin này, việc xác định một block là live hay dead trở nên đơn giản. Với một block D nằm trên đĩa tại địa chỉ A, hãy tra trong segment summary block để tìm **inode number** N và **offset** T của nó. Tiếp theo, tra trong **imap** để tìm vị trí hiện tại của inode N và đọc inode này từ đĩa (nếu inode đã ở trong bộ nhớ thì càng tốt). Cuối cùng, sử dụng offset T, tra trong inode (hoặc một indirect block) để xem inode cho rằng block thứ T của file này nằm ở đâu trên đĩa. Nếu nó trỏ chính xác tới địa chỉ đĩa A, LFS có thể kết luận block D là **live**. Nếu nó trỏ tới một địa chỉ khác, LFS có thể kết luận D không còn được sử dụng (tức là **dead**) và biết rằng phiên bản này không còn cần thiết.

Dưới đây là phần tóm tắt dưới dạng **pseudocode**:


Dưới đây là bản dịch tiếng Việt của đoạn văn bản bạn cung cấp, tuân thủ đầy đủ các yêu cầu đã nêu:


Hình dưới đây mô tả cơ chế, trong đó **segment summary block** (khối tóm tắt phân đoạn, ký hiệu SS) ghi lại rằng data block tại địa chỉ A0 thực chất là một phần của file *k* tại offset 0. Bằng cách kiểm tra **imap** của *k*, bạn có thể tìm thấy inode và thấy rằng nó thực sự trỏ tới vị trí đó.

...

Có một số cách rút gọn mà LFS sử dụng để làm cho quá trình xác định trạng thái sống (liveness) hiệu quả hơn. Ví dụ, khi một file bị **truncate** (cắt ngắn) hoặc bị xóa, LFS sẽ tăng **version number** (số phiên bản) của nó và ghi số phiên bản mới này vào imap. Bằng cách cũng ghi số phiên bản này vào segment trên đĩa, LFS có thể bỏ qua bước kiểm tra dài dòng đã mô tả ở trên chỉ bằng cách so sánh số phiên bản trên đĩa với số phiên bản trong imap, từ đó tránh được các thao tác đọc bổ sung.


## 43.11 Câu hỏi về chính sách: Block nào cần clean, và khi nào? (A Policy Question: Which Blocks To Clean, And When?)

Bên cạnh cơ chế đã mô tả ở trên, LFS phải bao gồm một tập hợp các **policy** (chính sách) để xác định cả **khi nào** cần clean và **block nào** đáng để clean. Việc xác định khi nào cần clean thì dễ hơn; có thể là định kỳ, trong thời gian hệ thống nhàn rỗi, hoặc khi bắt buộc vì đĩa đã đầy.

Việc xác định block nào cần clean thì khó hơn, và đã là chủ đề của nhiều bài báo nghiên cứu. Trong bài báo LFS gốc [RO91], các tác giả mô tả một phương pháp cố gắng phân tách **hot segment** và **cold segment**. Một hot segment là segment có nội dung thường xuyên bị ghi đè; do đó, với segment như vậy, chính sách tốt nhất là chờ lâu trước khi clean, vì càng ngày càng có nhiều block bị ghi đè (trong các segment mới) và do đó được giải phóng để sử dụng. Ngược lại, một cold segment có thể chỉ có một vài block chết nhưng phần còn lại của nội dung tương đối ổn định. Vì vậy, các tác giả kết luận rằng nên clean các cold segment sớm hơn và hot segment muộn hơn, và phát triển một heuristic (thuật toán kinh nghiệm) để thực hiện chính xác điều đó. Tuy nhiên, như hầu hết các chính sách khác, chính sách này không hoàn hảo; các phương pháp sau này đã chỉ ra cách làm tốt hơn [MR+97].


## 43.12 Khôi phục sau crash và Log (Crash Recovery And The Log)

Một vấn đề cuối cùng: điều gì xảy ra nếu hệ thống bị crash trong khi LFS đang ghi xuống đĩa? Như bạn có thể nhớ từ chương trước về journaling, crash trong quá trình cập nhật là một vấn đề khó đối với file system, và do đó LFS cũng phải xem xét.

Trong hoạt động bình thường, LFS buffer các thao tác ghi trong một segment, và sau đó (khi segment đầy hoặc khi một khoảng thời gian nhất định đã trôi qua) ghi segment đó xuống đĩa. LFS tổ chức các thao tác ghi này trong một **log**, tức là checkpoint region trỏ tới **head** và **tail segment**, và mỗi segment trỏ tới segment tiếp theo sẽ được ghi. LFS cũng định kỳ cập nhật checkpoint region. Crash rõ ràng có thể xảy ra trong một trong hai thao tác này (ghi một segment, ghi CR). Vậy LFS xử lý crash khi ghi các cấu trúc này như thế nào?

Hãy xét trường hợp thứ hai trước. Để đảm bảo việc cập nhật CR diễn ra **atomically** (nguyên tử), LFS thực tế giữ **hai CR**, một ở mỗi đầu của đĩa, và ghi luân phiên vào chúng. LFS cũng triển khai một giao thức cẩn thận khi cập nhật CR với các con trỏ mới nhất tới inode map và các thông tin khác; cụ thể, nó ghi ra một **header** (chứa timestamp), sau đó là phần thân của CR, và cuối cùng là một block cuối cùng (cũng chứa timestamp). Nếu hệ thống bị crash trong khi cập nhật CR, LFS có thể phát hiện điều này bằng cách thấy cặp timestamp không nhất quán. LFS sẽ luôn chọn sử dụng CR mới nhất có timestamp nhất quán, và do đó đảm bảo CR được cập nhật nhất quán.

Bây giờ xét trường hợp thứ nhất. Vì LFS ghi CR khoảng mỗi 30 giây, snapshot nhất quán cuối cùng của file system có thể đã khá cũ. Do đó, khi khởi động lại, LFS có thể dễ dàng khôi phục bằng cách chỉ cần đọc checkpoint region, các phần imap mà nó trỏ tới, và các file và thư mục tiếp theo; tuy nhiên, nhiều giây cập nhật cuối cùng sẽ bị mất.

Để cải thiện điều này, LFS cố gắng xây dựng lại nhiều segment đó thông qua một kỹ thuật được gọi là **roll forward** trong lĩnh vực cơ sở dữ liệu. Ý tưởng cơ bản là bắt đầu với checkpoint region cuối cùng, tìm điểm kết thúc của log (được bao gồm trong CR), và sau đó sử dụng nó để đọc qua các segment tiếp theo và xem có bản cập nhật hợp lệ nào trong đó không. Nếu có, LFS sẽ cập nhật file system tương ứng và do đó khôi phục được phần lớn dữ liệu và metadata đã ghi kể từ checkpoint cuối cùng. Xem luận án đoạt giải của Rosenblum để biết chi tiết [R92].


## 43.13 Tóm tắt (Summary)

LFS giới thiệu một cách tiếp cận mới để cập nhật đĩa. Thay vì ghi đè file tại chỗ, LFS luôn ghi vào một phần chưa sử dụng của đĩa, và sau đó thu hồi lại không gian cũ thông qua quá trình cleaning. Cách tiếp cận này, trong hệ thống cơ sở dữ liệu được gọi là **shadow paging** [L77] và trong lĩnh vực file system đôi khi được gọi là **copy-on-write**, cho phép ghi với hiệu năng rất cao, vì LFS có thể gom tất cả các bản cập nhật vào một segment trong bộ nhớ và sau đó ghi chúng ra cùng nhau theo thứ tự tuần tự.

>> **TIP: BIẾN KHUYẾT ĐIỂM THÀNH ƯU ĐIỂM**  
>> Bất cứ khi nào hệ thống của bạn có một khiếm khuyết cơ bản, hãy xem liệu bạn có thể biến nó thành một tính năng hoặc điều gì đó hữu ích hay không. **WAFL** của NetApp đã làm điều này với nội dung file cũ; bằng cách cung cấp các phiên bản cũ, WAFL không còn phải lo lắng về việc cleaning quá thường xuyên (mặc dù nó vẫn xóa các phiên bản cũ, cuối cùng, ở chế độ nền), và do đó vừa cung cấp một tính năng thú vị vừa loại bỏ phần lớn vấn đề cleaning của LFS chỉ trong một bước ngoặt tuyệt vời. Liệu có ví dụ nào khác như vậy trong các hệ thống không? Chắc chắn là có, nhưng bạn sẽ phải tự nghĩ ra, vì chương này đã kết thúc với chữ “O” viết hoa. Over. Done. Kaput. Hết. Peace!  

Các thao tác ghi lớn mà LFS tạo ra rất tốt cho hiệu năng trên nhiều loại thiết bị khác nhau. Trên ổ cứng, ghi lớn đảm bảo thời gian định vị được giảm thiểu; trên các RAID dựa trên parity như RAID-4 và RAID-5, chúng loại bỏ hoàn toàn vấn đề **small-write**. Các nghiên cứu gần đây thậm chí đã chỉ ra rằng các thao tác I/O lớn là cần thiết để đạt hiệu năng cao trên SSD dựa trên Flash [HK+17]; do đó, có thể khá bất ngờ, các file system kiểu LFS có thể là một lựa chọn tuyệt vời ngay cả cho các phương tiện lưu trữ mới này.

Nhược điểm của cách tiếp cận này là nó tạo ra **garbage**; các bản sao cũ của dữ liệu bị rải rác khắp đĩa, và nếu muốn thu hồi không gian này cho các lần sử dụng tiếp theo, ta phải định kỳ clean các segment cũ. Cleaning đã trở thành tâm điểm của nhiều tranh luận trong LFS, và lo ngại về chi phí cleaning [SS+95] có lẽ đã hạn chế tác động ban đầu của LFS trong lĩnh vực này. Tuy nhiên, một số file system thương mại hiện đại, bao gồm **WAFL** của NetApp [HLM94], **ZFS** của Sun [B07], và **btrfs** của Linux [R+13], và thậm chí cả các SSD hiện đại dựa trên Flash [AD14], áp dụng cách tiếp cận copy-on-write tương tự khi ghi xuống đĩa, và do đó di sản trí tuệ của LFS vẫn tiếp tục tồn tại trong các file system hiện đại này. Đặc biệt, WAFL đã vượt qua vấn đề cleaning bằng cách biến nó thành một tính năng; bằng cách cung cấp các phiên bản cũ của file system thông qua **snapshot**, người dùng có thể truy cập các file cũ khi họ lỡ tay xóa.