# Phần xen kẽ: Tệp và Thư mục (Interlude: Files and Directories)

Cho đến nay, chúng ta đã thấy sự hình thành của hai **abstraction** (lớp trừu tượng) quan trọng trong hệ điều hành: **process** (tiến trình) – là sự ảo hóa của CPU, và **address space** (không gian địa chỉ) – là sự ảo hóa của bộ nhớ.  
Kết hợp lại, hai abstraction này cho phép một chương trình chạy như thể nó đang ở trong một thế giới riêng tư, tách biệt; như thể nó có bộ xử lý (hoặc nhiều bộ xử lý) riêng; như thể nó có bộ nhớ riêng.  
Ảo tưởng này giúp việc lập trình hệ thống trở nên dễ dàng hơn rất nhiều, và vì thế ngày nay nó phổ biến không chỉ trên máy tính để bàn và máy chủ mà còn ngày càng xuất hiện trên mọi nền tảng lập trình được, bao gồm cả điện thoại di động và các thiết bị tương tự.

Trong phần này, chúng ta sẽ bổ sung một mảnh ghép quan trọng nữa vào bức tranh ảo hóa: **persistent storage** (lưu trữ bền vững).  
Một thiết bị lưu trữ bền vững, chẳng hạn như **ổ đĩa cứng** (hard disk drive) truyền thống hoặc **thiết bị lưu trữ thể rắn** (solid-state storage device) hiện đại, lưu trữ thông tin một cách lâu dài (hoặc ít nhất là trong một thời gian dài).  
Không giống như bộ nhớ, nơi dữ liệu bị mất khi mất điện, thiết bị lưu trữ bền vững giữ nguyên dữ liệu.  
Do đó, hệ điều hành phải đặc biệt cẩn trọng với loại thiết bị này: đây là nơi người dùng lưu trữ dữ liệu mà họ thực sự quan tâm.

### CRUX: QUẢN LÝ THIẾT BỊ LƯU TRỮ BỀN VỮNG NHƯ THẾ NÀO?

> Hệ điều hành nên quản lý một thiết bị lưu trữ bền vững như thế nào? Các API là gì? Những khía cạnh quan trọng trong triển khai là gì?

Vì vậy, trong vài chương tiếp theo, chúng ta sẽ khám phá các kỹ thuật quan trọng để quản lý dữ liệu bền vững, tập trung vào các phương pháp cải thiện hiệu năng và độ tin cậy.  
Tuy nhiên, trước tiên chúng ta sẽ bắt đầu với phần tổng quan về **API**: các giao diện mà bạn sẽ gặp khi tương tác với **UNIX file system** (hệ thống tệp UNIX).


## 39.1 Tệp và Thư mục (Files And Directories)

Hai abstraction quan trọng đã được phát triển theo thời gian trong quá trình ảo hóa lưu trữ.

**Abstraction** đầu tiên là **file** (tệp).  
Một file đơn giản là một mảng tuyến tính các byte, mỗi byte có thể được đọc hoặc ghi.  
Mỗi file có một dạng tên mức thấp nào đó, thường là một con số; người dùng thường không biết đến tên này.  
Vì lý do lịch sử, tên mức thấp của một file thường được gọi là **inode number** (số inode, hay i-number).  
Chúng ta sẽ tìm hiểu nhiều hơn về inode trong các chương sau; hiện tại, chỉ cần giả định rằng mỗi file có một inode number gắn liền với nó.

Trong hầu hết các hệ thống, hệ điều hành không biết nhiều về cấu trúc bên trong của file (ví dụ: nó là một bức ảnh, một tệp văn bản, hay mã C); thay vào đó, trách nhiệm của **file system** (hệ thống tệp) chỉ đơn giản là lưu trữ dữ liệu đó một cách bền vững trên đĩa và đảm bảo rằng khi bạn yêu cầu dữ liệu lần nữa, bạn nhận được đúng dữ liệu mà bạn đã lưu ban đầu.  
Làm được điều này không đơn giản như tưởng tượng!

**Abstraction** thứ hai là **directory** (thư mục).  
Một directory, giống như file, cũng có một tên mức thấp (tức inode number), nhưng nội dung của nó rất đặc thù: nó chứa một danh sách các cặp **(tên đọc được bởi người dùng, tên mức thấp)**.  
Ví dụ: giả sử có một file với tên mức thấp là “10”, và nó được người dùng gọi bằng tên “foo”.  
Directory chứa “foo” sẽ có một mục **(“foo”, “10”)** ánh xạ tên đọc được sang tên mức thấp.  
Mỗi mục trong một directory tham chiếu tới hoặc là file, hoặc là directory khác.  
Bằng cách đặt các directory bên trong các directory khác, người dùng có thể xây dựng một **directory tree** (cây thư mục) hoặc **directory hierarchy** (hệ phân cấp thư mục) tùy ý, trong đó tất cả file và directory đều được lưu trữ.

Cây thư mục bắt đầu từ **root directory** (thư mục gốc) – trong các hệ thống dựa trên UNIX, thư mục gốc được ký hiệu đơn giản là `/` – và sử dụng một ký tự phân tách nào đó để đặt tên các thư mục con tiếp theo cho đến khi chỉ ra được file hoặc directory mong muốn.  
Ví dụ: nếu một người dùng tạo một thư mục `foo` trong thư mục gốc `/`, và sau đó tạo một file `bar.txt` trong thư mục `foo`, chúng ta có thể tham chiếu tới file này bằng **absolute pathname** (đường dẫn tuyệt đối), trong trường hợp này sẽ là:

```
/foo/bar.txt
```

**Hình 39.1: Ví dụ về cây thư mục (An Example Directory Tree)**

> **TIP: SUY NGHĨ CẨN THẬN VỀ VIỆC ĐẶT TÊN**  
>  
> Đặt tên (**naming**) là một khía cạnh quan trọng của các hệ thống máy tính. Trong các hệ thống UNIX, hầu như mọi thứ bạn có thể nghĩ tới đều được đặt tên thông qua **file system** (hệ thống tệp). Không chỉ các file, mà cả thiết bị (**device**), ống dẫn (**pipe**), và thậm chí cả **process** (tiến trình) cũng có thể được tìm thấy trong một cấu trúc trông giống như một hệ thống tệp thông thường.  
> Sự thống nhất trong cách đặt tên này giúp đơn giản hóa mô hình khái niệm của bạn về hệ thống, và làm cho hệ thống trở nên đơn giản hơn và có tính mô-đun cao hơn. Vì vậy, bất cứ khi nào tạo một hệ thống hoặc giao diện, hãy suy nghĩ kỹ về những cái tên bạn đang sử dụng.

Các **directory** (thư mục) và **file** (tệp) có thể trùng tên miễn là chúng nằm ở các vị trí khác nhau trong cây hệ thống tệp.  
Ví dụ: có thể tồn tại hai file tên `bar.txt` như trong hình minh họa: `/foo/bar.txt` và `/bar/foo/bar.txt`.


## 39.2 Giao diện hệ thống tệp (The File System Interface)

Bây giờ, chúng ta sẽ thảo luận chi tiết hơn về **file system interface** (giao diện hệ thống tệp).  
Chúng ta sẽ bắt đầu với những thao tác cơ bản: tạo, truy cập và xóa file.  
Bạn có thể nghĩ rằng điều này khá đơn giản, nhưng trong quá trình tìm hiểu, chúng ta sẽ khám phá một **system call** bí ẩn được dùng để xóa file, gọi là `unlink()`.  
Hy vọng rằng, đến cuối chương này, lời giải cho “bí ẩn” đó sẽ trở nên rõ ràng với bạn.


## 39.3 Tạo file (Creating Files)

Chúng ta sẽ bắt đầu với thao tác cơ bản nhất: **tạo một file**.  
Điều này có thể thực hiện được với **system call** `open`; bằng cách gọi `open()` và truyền vào cờ (**flag**) `O_CREAT`, một chương trình có thể tạo ra một file mới.  
Dưới đây là ví dụ mã nguồn để tạo một file tên “foo” trong **current working directory** (thư mục làm việc hiện tại):

```c
int fd = open("foo", O_CREAT|O_WRONLY|O_TRUNC, S_IRUSR|S_IWUSR);
```

> **ASIDE: SYSTEM CALL CREAT()**  
>  
> Cách cũ hơn để tạo file là gọi `creat()`, như sau:  
>  
> ```c
> // tùy chọn: thêm tham số thứ hai để thiết lập quyền truy cập
> int fd = creat("foo");
> ```  
>  
> Bạn có thể coi `creat()` tương đương với `open()` với các cờ: `O_CREAT | O_WRONLY | O_TRUNC`.  
> Vì `open()` có thể tạo file, nên việc sử dụng `creat()` đã phần nào ít phổ biến hơn.  
> Tuy nhiên, nó vẫn giữ một vị trí đặc biệt trong “truyền thuyết” UNIX.  
> Cụ thể, khi Ken Thompson được hỏi ông sẽ làm gì khác nếu thiết kế lại UNIX, ông trả lời:  
> “Tôi sẽ viết `creat` với một chữ e” (tức là `create`).

Một khía cạnh quan trọng của `open()` là giá trị nó trả về: **file descriptor** (bộ mô tả tệp).  
File descriptor chỉ đơn giản là một số nguyên, riêng cho mỗi **process** (tiến trình), và được dùng trong các hệ thống UNIX để truy cập file.

Các file descriptor được hệ điều hành quản lý **theo từng process**.  
Điều này có nghĩa là một cấu trúc dữ liệu đơn giản nào đó (ví dụ: một mảng) được lưu trong **proc structure** (cấu trúc tiến trình) trên các hệ thống UNIX.  
Dưới đây là phần liên quan từ **xv6 kernel**:


## 39.4 Đọc và ghi tệp (Reading And Writing Files)

Khi đã có một số file, tất nhiên chúng ta sẽ muốn đọc hoặc ghi chúng.  
Hãy bắt đầu bằng việc đọc một file đã tồn tại.  
Nếu đang gõ lệnh trong **command line** (dòng lệnh), chúng ta có thể dùng chương trình `cat` để hiển thị nội dung của file ra màn hình.

```sh
prompt> echo hello > foo
prompt> cat foo
hello
prompt>
```

Để tìm hiểu điều gì thực sự xảy ra, chúng ta sẽ sử dụng một công cụ cực kỳ hữu ích để **theo dõi các system call** mà một chương trình thực hiện.  
Trên Linux, công cụ này được gọi là `strace`.  
Dưới đây là ví dụ sử dụng `strace` để tìm hiểu `cat` đang làm gì (một số lời gọi đã được lược bỏ để dễ đọc):

...

Tại sao lần gọi `open()` đầu tiên lại trả về **3**, chứ không phải **0** hoặc **1**?  
Hóa ra, mỗi **process** (tiến trình) đang chạy đã mặc định mở sẵn **ba file**:

- **standard input** (stdin – bộ mô tả tệp số 0)  
- **standard output** (stdout – bộ mô tả tệp số 1)  
- **standard error** (stderr – bộ mô tả tệp số 2)

Sau khi `open` thành công, `cat` sử dụng **system call** `read()` để liên tục đọc một số byte từ file.  
Chương trình sau đó cố gắng đọc thêm, nhưng vì không còn byte nào, `read()` trả về **0** và chương trình hiểu rằng nó đã đọc hết toàn bộ file.  
Do đó, chương trình gọi `close()` để báo rằng nó đã hoàn tất.


## 39.5 Đọc và ghi, nhưng không theo tuần tự (Reading And Writing, But Not Sequentially)

Đôi khi, chúng ta cần đọc hoặc ghi tại một **offset** (vị trí bù) cụ thể trong file.  
Để làm điều này, ta sử dụng **system call** `lseek()`:

```c
off_t lseek(int fildes, off_t offset, int whence);
```

Tham số `whence` xác định chính xác cách dịch chuyển con trỏ file:

- **SEEK_SET**: đặt offset hiện tại thành `offset` byte.  
- **SEEK_CUR**: đặt offset thành vị trí hiện tại cộng thêm `offset` byte.  
- **SEEK_END**: đặt offset thành kích thước file cộng thêm `offset` byte.

Với mỗi file mà một process mở, hệ điều hành sẽ theo dõi một **offset hiện tại** (current offset), xác định vị trí bắt đầu cho lần đọc hoặc ghi tiếp theo.  
Offset này được cập nhật **ngầm** khi gọi `read` hoặc `write`, hoặc **tường minh** khi gọi `lseek`.  
Offset này được lưu trong **struct file**.  
Dưới đây là định nghĩa (đơn giản hóa) của cấu trúc này trong **xv6**:

```c
struct file {
  int ref;
  char readable;
  char writable;
  struct inode *ip;
  uint off;
};
```

> **ASIDE: GỌI LSEEK() KHÔNG THỰC HIỆN DISK SEEK**  
>  
> Tên gọi của system call `lseek()` dễ gây nhầm lẫn cho nhiều sinh viên.  
> Lời gọi `lseek()` chỉ đơn giản thay đổi một biến trong bộ nhớ của hệ điều hành, biến này theo dõi offset hiện tại.  
> **Disk seek** (dịch chuyển đầu đọc đĩa) chỉ xảy ra khi một thao tác đọc hoặc ghi tới đĩa nằm trên một track khác so với thao tác trước đó.  
> Gọi `lseek()` có thể dẫn đến một disk seek trong thao tác đọc hoặc ghi tiếp theo, nhưng bản thân nó **không hề** gây ra bất kỳ I/O vật lý nào.

Hãy theo dõi một process mở một file (kích thước 300 byte) và đọc nó bằng cách gọi `read()` nhiều lần, mỗi lần đọc 100 byte.


## 39.6 Chia sẻ entry trong bảng file mở: fork() và dup() (Shared File Table Entries: fork() And dup())

Trong nhiều trường hợp, ánh xạ từ **file descriptor** (bộ mô tả tệp) tới một entry trong **open file table** (bảng file mở) là ánh xạ **một-một**.  
Tuy nhiên, có một số trường hợp thú vị khi một entry trong open file table được **chia sẻ**.  
Một trong những trường hợp đó xảy ra khi **process cha** tạo ra **process con** bằng `fork()`.

**Hình 39.2: Chia sẻ entry bảng file giữa tiến trình cha/con (fork-seek.c)**

Khi chạy chương trình này, chúng ta thấy kết quả sau:

```sh
prompt> ./fork-seek
child: offset 10
parent: offset 10
prompt>
```

Một trường hợp chia sẻ khác xảy ra với **system call** `dup()`.  
Lời gọi `dup()` cho phép một **process** (tiến trình) tạo ra một **file descriptor** (bộ mô tả tệp) mới tham chiếu tới **cùng một file đã mở** (open file) như một descriptor hiện có.

...

**Hình 39.4: Chia sẻ entry bảng file với dup() (dup.c)**


## 39.7 Ghi ngay lập tức với fsync() (Writing Immediately With fsync())

Thông thường, khi một chương trình gọi `write()`, **file system** (hệ thống tệp) sẽ **buffer** (đệm) các thao tác ghi này trong bộ nhớ một thời gian vì lý do hiệu năng.  
Tuy nhiên, một số ứng dụng yêu cầu khả năng **ép** dữ liệu được ghi xuống đĩa ngay lập tức.

Để hỗ trợ các ứng dụng loại này, hầu hết các file system cung cấp **system call**:

```c
int fsync(int fd);
```

Khi một process gọi `fsync()`, file system sẽ buộc tất cả dữ liệu **dirty** (chưa được ghi xuống đĩa) của file được tham chiếu bởi file descriptor chỉ định phải được ghi xuống đĩa.


## 39.8 Đổi tên file (Renaming Files)

Để đổi tên một file, lệnh `mv` sử dụng **system call**:

```c
int rename(char *old, char *new);
```

Một đảm bảo thú vị mà `rename()` cung cấp là nó (thường) được triển khai như một lời gọi **atomic** (nguyên tử) đối với các sự cố **system crash** (sập hệ thống).  
Điều này rất quan trọng đối với các ứng dụng yêu cầu cập nhật trạng thái file một cách nguyên tử.  
Ví dụ, một trình soạn thảo file có thể thực hiện các bước sau để lưu thay đổi một cách an toàn:

...

Bước cuối cùng này **hoán đổi nguyên tử** file mới vào vị trí, đồng thời xóa phiên bản cũ của file.


## 39.9 Lấy thông tin về file (Getting Information About Files)

File system lưu trữ khá nhiều thông tin về mỗi file, mà chúng ta thường gọi là **metadata** (siêu dữ liệu).  
Để xem metadata của một file cụ thể, chúng ta có thể sử dụng **system call** `stat()` hoặc `fstat()`.  
Các lời gọi này sẽ điền thông tin vào một cấu trúc `stat`:

...

**Hình 39.5: Cấu trúc stat (The stat structure)**

Bạn cũng có thể sử dụng công cụ dòng lệnh `stat` để xem thông tin này.


## 39.10 Xóa file (Removing Files)

...

(TODO)