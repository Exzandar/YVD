# TODO: handle the progress bar when downloading audio and video
# TODO: show the file size in the results
# TODO: make it more fast
# TODO: run ffmpeg where this file is located, not from C:\
# TODO: deal with captions and descriptions
# TODO: add the play option to start the file downloaded
# TODO: do things when download finished
# TODO: add files downloaded to a text file and check them every time

# TODO: handle signal conditions
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUiType
import sys
import os
import subprocess
from pytube import YouTube, Playlist, helpers, exceptions
from pathlib import Path
from urllib import error
from datetime import timedelta

MainUI, _ = loadUiType('design.ui')                     # upload the application UI file designed by QT Designer


class W_Signal(QObject):                    # Signals to deal with slots used in Threads, should inherent from QObject
    progress_sig = pyqtSignal(int)
    error_sig = pyqtSignal(tuple)           # error signal
    finished_sig = pyqtSignal(int)
    regx_err = pyqtSignal(int)              # regex error, thread two signal
    not_available = pyqtSignal(int)
    url_connection = pyqtSignal(int)
    thrd_tw = pyqtSignal(int)
    thrd_one_error = pyqtSignal(int)
    download_error = pyqtSignal(int)
    thrd_tw_gnrl_err = pyqtSignal(int)
    thrd_3_PL_gd = pyqtSignal(int)          # play list as all has no error
    thrd_3_PL_bd = pyqtSignal(int)          # play list as all has errors
    thrd_3_PL_yt_gd = pyqtSignal(int)       # video in play list has no error
    thrd_3_PL_yt_bd = pyqtSignal(int)       # video in play list has error


class Thread_One(QRunnable):
    """
    - This is Thread number.1
    - It inherent from QRunnable to use it with different threads and to be easy to handle and manage.
    - This thread used to Download and merge the outputs and sending signals to progressBar and so on.
    - The code of the thread starts at run() function.
    - It takes 5 arguments [url, option, res, path, name]
    """
    def __init__(self, fetched_url, fetched_option, fetched_resolution, fetched_path, fetched_name='exzandar'):
        QRunnable.__init__(self)
        self.signals = W_Signal()                   # Create an instance from signals to use with slots inside the thread
        self.title = ''
        self.file_size = 0
        self.value_remaining = 0
        self.down_err = 0
        self.YT = ''
        self.fetched_url = fetched_url
        self.fetched_option = fetched_option
        self.fetched_resolution = fetched_resolution
        self.fetched_path = fetched_path
        self.fetched_name = fetched_name

    def down(self, url, res, path, name='exzandar', option='C'):
        """
        - This function to start the downloading process of videos
        :param url: The YouTube url of the video
        :param res: The wanted resolution of the video
        :param path: The wanted locally path to save the video
        :param name: The wanted name to rename the video instead of its default name
        :param option: {'A':"For downloading audio only", 'V':"Foe downloading the video only",
                        'C':"For downloading Audio&Video then merge them by FFmpeg,
                        'AC':"For downloading the Clip & Audio"}
        :return: It returns NoThing :""
        """
        self.YT = YouTube(str(url), on_progress_callback=self.down_progrs)
        self.title = self.YT.title             # The video Title
        if option == 'A':                 # Downloading Audio only
            res = 'mp4'
            st = self.YT.streams               # to get the streams available for downloading
            st = st.get_audio_only(res)   # edit this to be with quality rather than mp4
            self.file_size = int(st.filesize)
            print("\nsize: ", self.file_size)       # edit this to write it in statue
            st.download(output_path=path)    # no edit to file names, single file
        elif option == 'V':
            st = self.YT.streams
            st = st.filter(res=res, adaptive=True, type="video", mime_type="video/mp4").first()  # to get the video
            self.file_size = int(st.filesize)       # TODO: handle the file size
            print("\nsize: ", self.file_size)  # edit this to write it in statue
            st.download(output_path=path)    # no edit to the file names
        elif (option == 'C') or (option == 'AC'):
            st = self.YT.streams
            vd = st.filter(res=res, adaptive=True, type="video", mime_type="video/mp4").first()  # to get the video
            ad = st.get_audio_only("mp4")
            total_siz = vd.filesize + ad.filesize
            print("downloading vid and aud")        # TODO: handle the progress bar to care the two values
            self.file_size = vd.filesize
            self.vd_path = vd.download(output_path=path)
            self.file_size = ad.filesize
            self.ad_path = ad.download(output_path=path, filename=(ad.title+" - aud"))
            print("finished vid and aud")
            self.merge_and_output()

    def down_progrs(self, stream=None, chunk=None, bytes_remaining=None):
        self.value_remaining = (self.file_size - bytes_remaining) / self.file_size * 100
        self.signals.progress_sig.emit(self.value_remaining)        # send signal with value of remaining percent to Main()

    def merge_and_output(self):
        print("\n[+++++] Download completed, now it's time to merge the video and audio!\n")
        aud_path = ('"' + str(self.fetched_path) + '\\' + helpers.safe_filename(self.title) + ' - aud' + '.mp4"')
        vid_path = ('"' + str(self.fetched_path) + '\\' + helpers.safe_filename(self.title) + '.mp4"')
        mrg_path = ('"' + str(self.fetched_path) + '\\' + helpers.safe_filename(self.title) + ' -- output.mp4"')
        subprocess.run('ffmpeg -i {} -i {} -c:v copy -c:a aac {} -y'.format(vid_path, aud_path, mrg_path))     # -y: overwrite without asking
        if self.fetched_option == 'C':
            os.system("DEL {} {}".format(aud_path, vid_path))
        elif self.fetched_option == "AC":
            os.system("DEL {}".format(vid_path))
        print("\n***** Sorry for this mess, we almost finished ^_^ *****\n")

    def run(self):
        try:
            self.down(self.fetched_url, self.fetched_resolution, self.fetched_path, self.fetched_name, self.fetched_option)
        except:
            print("error, error, error")
            self.down_err = 1
            self.signals.download_error.emit(self.down_err)


class Thread_two(QRunnable):
    def __init__(self, url):
        QRunnable.__init__(self)
        self.url = url
        self.signals = W_Signal()
        self.rgx_err = 0
        self.not_avlbl = 0
        self.conn_err = 0
        self.gnrl_err_trd_tw = 0
        self.thrd_finshed = 0
        self.title = ''
        self.length = 0
        self.views = 0
        self.vid_id = ''
        self.rating = ''

    def run(self):
        try:
            yt = YouTube(self.url)
            self.title = yt.title
            self.length = yt.length
            self.views = yt.views
            self.vid_id = yt.video_id
            self.rating = yt.rating
            self.signals.regx_err.emit(self.rgx_err)       # if no err, send signal with False value
        except exceptions.RegexMatchError:
            self.rgx_err = 1                               # there is an err, send value with True
            self.signals.regx_err.emit(self.rgx_err)
        except exceptions.VideoUnavailable:
            self.not_avlbl = 1                              # video isn't available
            self.signals.not_available.emit(self.not_avlbl)
        except error.URLError:
            self.conn_err = 1
            self.signals.url_connection.emit(self.conn_err)
        except:
            self.gnrl_err_trd_tw = 1
            self.signals.thrd_tw_gnrl_err.emit(self.gnrl_err_trd_tw)
        self.thrd_finshed = 1                               # when thread two is finished
        self.signals.thrd_tw.emit(self.thrd_finshed)


class Thread_Three(QRunnable):
    def __init__(self, play_list_url, pl_res='720p', pl_path=''):
        QRunnable.__init__(self)
        self.playlist_num = 1
        self.thrd_3_signals = W_Signal()
        self.play_list_url = play_list_url
        self.pl_res = pl_res
        self.pl_path = pl_path
        self.PL_title = ''
        self.PL_id = ''
        self.urls = []
        self.single_yt = ''
        self.single_yt_title = ''
        self.single_yt_length = ''
        self.single_yt_id = ''
        self.single_yt_url = ''
        self.thrd_3_sig_1 = 0
        self.thrd_3_sig_2 = 0
        self.thrd_3_sig_3 = 0
        self.thrd_3_sig_4 = 0
        self.aud_downloaded_err = 0
        self.vid_downloaded_err = 0
        self.aud_stream = ''
        self.vid_stream = ''
        self.counter_vids = 0
        self.value_remaining = 0
        self.file_size = 0

    def down_progrs(self, stream=None, chunk=None, bytes_remaining=None):
        self.value_remaining = (self.file_size - bytes_remaining) / self.file_size * 100
        self.thrd_3_signals.progress_sig.emit(self.value_remaining)

    def pl_download(self, url):
        try:
            self.single_yt = YouTube(url, on_progress_callback=self.down_progrs)
            self.single_yt_title = helpers.safe_filename(self.single_yt.title)  # to make it valid in systems
            self.single_yt_length = self.single_yt.length
            self.single_yt_id = self.single_yt.video_id
            self.aud_stream = self.single_yt.streams.get_audio_only("mp4")
            self.vid_stream = self.single_yt.streams.filter(res=self.pl_res, adaptive=True, type="video", mime_type="video/mp4").first()
            self.file_size = self.vid_stream.filesize
            self.single_yt.streams.filter(res=self.pl_res, adaptive=True, type="video",
                                          mime_type="video/mp4").first().download(output_path=self.pl_path)
            self.file_size = self.aud_stream.filesize
            self.single_yt.streams.get_audio_only("mp4").download(output_path=self.pl_path, filename=self.single_yt_title+" - aud")
        except error.URLError:
            print("url error")
            self.aud_downloaded_err = 1
            self.vid_downloaded_err = 1
            return False
        except exceptions.RegexMatchError:
            print("rgx err")
            return False
        except OSError:
            print("sockets err, internet lost")
            return False
        except AttributeError:
            print("attribute err")
            return False
        return True

    def pl_merge(self):
        # merge vid, aud and get the output
        print("\n[+++++] Download completed, now it's time to merge the video and audio!\n")

        aud_path = ('"' + str(self.pl_path) + '\\' + helpers.safe_filename(self.single_yt_title) + ' - aud' + '.mp4"')
        vid_path = ('"' + str(self.pl_path) + '\\' + helpers.safe_filename(self.single_yt_title) + '.mp4"')
        mrg_path = ('"' + str(self.pl_path) + '\\' + helpers.safe_filename(self.single_yt_title) + ' -- output.mp4"')
        subprocess.run('ffmpeg -i {} -i {} -c:v copy -c:a aac {} -y'.format(vid_path, aud_path, mrg_path))  # -y: overwrite without asking
        os.system("DEL {} {}".format(aud_path, vid_path))
        #os.system("DEL {}".format(vid_path))
        print("\n***** Sorry for this mess, we almost finished ^_^ *****\n")

    def run(self):
        try:
            p_l = Playlist(self.play_list_url)
            self.urls = p_l.video_urls
            self.PL_title = p_l.title
            self.PL_id = p_l.playlist_id
            # good playlist
            self.thrd_3_sig_1 = 1
            self.thrd_3_signals.thrd_3_PL_gd.emit(self.thrd_3_sig_1)
            print("playlist is a good one:''")
        except:
            # bad playlist
            print("playlist is a bad one:''")
            self.thrd_3_sig_2 = 1
            self.thrd_3_signals.thrd_3_PL_bd.emit(self.thrd_3_sig_2)
            return False
        else:
            for url in self.urls:
                if self.pl_download(url):
                    self.pl_merge()
                    print("complete one")
                    self.counter_vids += 1
                    self.thrd_3_sig_3 = 1
                    self.thrd_3_signals.thrd_3_PL_yt_gd.emit(self.thrd_3_sig_3)
                else:
                    self.thrd_3_sig_4 = 1
                    self.thrd_3_signals.thrd_3_PL_yt_bd.emit(self.thrd_3_sig_4)
                    print("bad one")
        finally:
            print("The whole playlist is finished now, we are done ^_^ ")


class Main(QWidget, MainUI):
    def __init__(self, parent=None):
        super(Main, self).__init__(parent)
        QWidget.__init__(self)
        self.setupUi(self)
        self.url = ''                       # the url in self.le_url
        self.brws_f = ''                    # the location in browse_file()
        self.save_path = ''                 # edited location in brws_f, that val will be passed to Thread
        self.path_checked = False
        self.thread_pool = QThreadPool()    # create instance from QThreadPool to manage threads of QRunnable
        self.edit_buttons()                 # if there are any edits on buttons
        self.banner()                       # intro banner
        self.connectionerror = False
        self.res = ''                       # the value in self.combobox_res
        self.option = ''                    # the value checked in rd_a, rd_v, rd_c, rd_ac

    def banner(self):
        self.le_statue.setText("\t\t\t\t YouTube Video Downloader\n"
                               "[->]  Y-V-D is a simple program to download videos and audios from Youtube by the wanted quality.\n"
                               "[->]  Author: Ibrahem Mohamed AKA: exzandar or MagMada.\n"
                               "[->]  If you want to find me, just type exzandar in google search.\n"
                               "[->]  My personal Blog: https://exzandar.home.blog\n"
                               "\t\t==================================================\n")

    def edit_buttons(self):
        # Deactivate widgets to handle everything separately, and leave the search button activated.
        self.combobox_res.setEnabled(False)
        self.rd_a.setEnabled(False)
        self.rd_v.setEnabled(False)
        self.rd_c.setEnabled(False)
        self.rd_ac.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.label_file_path.setText("Choose a path to save files in")

    def browse_file(self):
        # Create a widget to browse files and return the saving path
        self.brws_f = QFileDialog.getExistingDirectory(self, 'Select Folder')
        self.save_path = Path(self.brws_f)
        self.label_file_path.setText('File will be saved in: ' + str(self.save_path))
        self.path_checked = True
        self.download_btn.setEnabled(True)

    def download(self):
        self.lcdNumber.display(0)
        self.url = self.le_url.text()       # the value of the URL
        self.res = self.combobox_res.currentText()              # the value of combo box, output ex: 720p
        self.le_statue.append("[+] Resolution chosen is " + self.res)
        # add the playlist option
        if 'list' in self.url:
            self.le_statue.append("\n[+] This is a playlist, waiting to get information .. Be patient.")
            self.play_list(self.url, self.res, self.save_path)
            self.download_btn.setEnabled(False)

        else:
            if self.rd_a.isChecked():
                self.option = "A"
                self.le_statue.append("\n[+] Audio only ... Waiting to get the file details ...")
                self.thread_one = Thread_One(self.url, self.option, self.res, self.save_path)
                self.thread_one.signals.progress_sig.connect(self.progress_value)
                self.thread_one.signals.thrd_one_error.connect(self.test)       # error in downloading, "thread one"
                self.thread_one.signals.download_error.connect(self.test_thread_one)       # error while downloading
                self.thread_pool.start(self.thread_one)
            elif self.rd_v.isChecked():
                self.le_statue.append("\n[+] video only ... Waiting to get the file details ...")
                self.option = "V"
                self.thread_one = Thread_One(self.url, self.option, self.res, self.save_path)
                self.thread_pool.start(self.thread_one)
                self.thread_one.signals.progress_sig.connect(self.progress_value)
                self.thread_one.signals.thrd_one_error.connect(self.test)  # error in downloading, "thread one"
                self.thread_one.signals.download_error.connect(self.test_thread_one)  # error while downloading
            elif self.rd_c.isChecked():
                self.option = 'C'
                self.le_statue.append("\n[+] clip only")
                self.thread_one = Thread_One(self.url, self.option, self.res, self.save_path)
                self.thread_pool.start(self.thread_one)
                self.thread_one.signals.progress_sig.connect(self.progress_value)
                self.thread_one.signals.thrd_one_error.connect(self.test)  # error in downloading, "thread one"
                self.thread_one.signals.download_error.connect(self.test_thread_one)  # error while downloading
            elif self.rd_ac.isChecked():
                self.option = "AC"
                self.le_statue.append("\n[+] Audio and clip")
                self.thread_one = Thread_One(self.url, self.option, self.res, self.save_path)
                self.thread_pool.start(self.thread_one)
                self.thread_one.signals.progress_sig.connect(self.progress_value)
                self.thread_one.signals.thrd_one_error.connect(self.test)  # error in downloading, "thread one"
                self.thread_one.signals.download_error.connect(self.test_thread_one)  # error while downloading
            # ========== save location ================
            if self.path_checked:
                self.le_statue.append("[+] File will be saved in: " + str(self.save_path))
            else:
                QMessageBox.critical(self, 'Path Error 404', 'Please enter a valid Path to save files in.')
            # ==============================================================

    def url_check(self, url):
        # delete this in the future
        if "youtube.com" in url:
            if "list" in url:
                #self.le_statue.append("\n[+] This is a playlist ...")
                return "list"
            elif "watch" in url:
                #self.le_statue.append("\n[+] This is a single video ...")
                return "single"
        else:
            #self.le_statue.append("\n==+=+== This is not a YouTube link Bitch! ==+=+==")
            return False  #"URL isn't valid, try another one"

    def get_data(self):
        self.url = self.le_url.text()       # get the value stored in the url label "self.le_url"
        self.banner()                       # get banner after every search result
        self.progressbar.setValue(0)        # set the progress bar to zero
        if 'list' in self.url:
            self.combobox_res.setEnabled(True)
            self.rd_c.setEnabled(True)
            self.save_btn.setEnabled(True)
        else:
            self.thread_two = Thread_two(self.url)
            self.thread_two.signals.regx_err.connect(self.test)
            self.thread_two.signals.not_available.connect(self.test)
            self.thread_two.signals.url_connection.connect(self.test)
            self.thread_two.signals.thrd_tw_gnrl_err.connect(self.test)
            self.thread_pool.start(self.thread_two)
            self.thread_two.signals.thrd_tw.connect(self.handle_res_opt)

    def handle_res_opt(self):
        if self.thread_two.conn_err or self.thread_two.not_avlbl or self.thread_two.rgx_err:      # if there are errors, options will not be available
            pass
        else:
            self.combobox_res.setEnabled(True)
            self.rd_a.setEnabled(True)
            self.rd_v.setEnabled(True)
            self.rd_c.setEnabled(True)
            self.rd_ac.setEnabled(True)
            self.save_btn.setEnabled(True)
            if self.thread_two.thrd_finshed:
                pass

    def progress_value(self):
        print("signal arrived")
        self.progressbar.setValue(int(self.thread_one.value_remaining))
        print(self.thread_one.value_remaining)

    def progress_playlist(self):
        print("signal arrived")
        self.progressbar.setValue(int(self.thread_three.value_remaining))
        print(self.thread_three.value_remaining)

    def play_list(self, url, res, path):
        self.test_thrd_pool = QThreadPool()
        self.thread_three = Thread_Three(play_list_url=url, pl_res=res, pl_path=path)
        self.test_thrd_pool.start(self.thread_three)
        self.thread_three.thrd_3_signals.thrd_3_PL_gd.connect(self.thrd_3_sig)
        self.thread_three.thrd_3_signals.thrd_3_PL_bd.connect(self.thrd_3_sig)
        self.thread_three.thrd_3_signals.thrd_3_PL_yt_bd.connect(self.thrd_3_sig)
        self.thread_three.thrd_3_signals.thrd_3_PL_yt_gd.connect(self.thrd_3_sig)
        self.thread_three.thrd_3_signals.progress_sig.connect(self.progress_playlist)
        print("starting the playlist process")

    def thrd_3_sig(self):
        # thrd reciever
        # =============
        if self.thread_three.thrd_3_sig_1:          # playlist is valid
            self.le_statue.append("[+] Getting playlist details ...")
            self.le_statue.append("[+] PlayList ID: {}".format(self.thread_three.PL_id))
            self.le_statue.append("[+] PlayList Title: {}".format("play list 1"))
            self.le_statue.append("[+] Videos num: {}".format(len(self.thread_three.urls)))
            self.lcdNumber_2.display(len(self.thread_three.urls))
            self.thread_three.thrd_3_sig_1 = 0    # to return the value to 0 and not show the data again
        if self.thread_three.thrd_3_sig_2:        # playlist isn't valid
            QMessageBox.information(self, "Connection Error", "An Error occurred while getting PlayList details, try again.")
        if self.thread_three.thrd_3_sig_3:        # counter of videos downloaded
            self.thread_three.thrd_3_sig_3 = 0      # make it zero to avoiding over count the false vids
            num = self.lcdNumber.intValue()
            x = num+1
            num = self.lcdNumber.display(num+1)
            self.le_statue.append("[{}] Vid {} Downloaded".format(x, self.thread_three.single_yt_title))
            self.progressbar.setValue(0)
        if self.thread_three.thrd_3_sig_4:
            QMessageBox.information(self, "Download Error", "Can't download this video '{}', it might be deleted, unavailable or old or the error maybe in your connection".format(self.thread_three.single_yt_title))
            self.le_statue.append("Can't download this video {}, it might be deleted, unavailable or old".format(self.thread_three.single_yt_title))
            self.progressbar.setValue(0)

    def test_btn(self):
        pass

    def prog_exit(self):
        self.thread_pool.waitForDone(50)
        exit()

    def test(self):
        if self.thread_two.rgx_err:
            QMessageBox.information(self, 'Not valid link!', "Try a valid YouTube link, Bitch!")
        elif self.thread_two.not_avlbl:
            QMessageBox.information(self, 'Not Available video', "Video trying to download isn't available")
        elif self.thread_two.conn_err:
            QMessageBox.information(self, 'Connection Error', "There is a connection error, try again when your internet being stable.")
        elif self.thread_two.gnrl_err_trd_tw:
            QMessageBox.information(self, 'Unexpected', "Unexpected error, Just try again.")
            self.edit_buttons()
        else:
            length = timedelta(seconds=self.thread_two.length)
            self.le_statue.append("\n[+] Title: " + str(self.thread_two.title))
            self.le_statue.append("[+] Length: " + str(length))
            self.le_statue.append("[+] Views: " + str(self.thread_two.views))
            self.le_statue.append("[+] Video ID: " + str(self.thread_two.vid_id))
            self.le_statue.append("[+] Rating: " + str(self.thread_two.rating))

    def test_thread_one(self):
        if self.thread_one.down_err:
            QMessageBox.information(self, 'Connection lost!', "Error occurred while downloading")
            self.edit_buttons()

    def finished_download(self):
        pass


def main():
    app = QApplication(sys.argv)
    window = Main()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()