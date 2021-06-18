if [ "$#" -ne 1 ];
then 
	echo 'Error: expected one argument (name of the project)'
	exit 2
fi

name=$1
rm -rf "../$name"
mkdir "../$name"
pyinstaller -y engine.spec "$name"
mv "dist/$name" "../$name/$name"
cp utilities/audio_dlls/* "../$name/$name"
cp -r favicon.ico "../$name/$name"
cp utilities/install/double_click_to_play.bat "../$name"
rm -rf build
rm -rf dist
echo Done
exit 0