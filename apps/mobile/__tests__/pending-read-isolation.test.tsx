import React from 'react';
import { Text } from 'react-native';
import { act, render, waitFor } from '@testing-library/react-native';
import { useAsync } from '../src/lib/useAsync';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

function Panel({ hotel, request }: { hotel: 'A' | 'B'; request: (hotel: 'A' | 'B') => Promise<string> }) {
  const { data, loading } = useAsync(() => request(hotel), [hotel, request]);
  return <>
    <Text testID="hotel">{hotel}</Text>
    <Text testID="data">{data ?? 'none'}</Text>
    <Text testID="loading">{String(loading)}</Text>
  </>;
}

it('never applies an old PMS/Inbox read after the hotel identity changes', async () => {
  const a = deferred<string>();
  const b = deferred<string>();
  const request = jest.fn((hotel: 'A' | 'B') => hotel === 'A' ? a.promise : b.promise);
  const screen = render(<Panel hotel="A" request={request} />);
  expect(screen.getByTestId('data').props.children).toBe('none');

  screen.rerender(<Panel hotel="B" request={request} />);
  await waitFor(() => expect(request).toHaveBeenCalledWith('B'));
  await act(async () => { a.resolve('A-only guest content'); await a.promise; });
  expect(screen.getByTestId('hotel').props.children).toBe('B');
  expect(screen.getByTestId('data').props.children).toBe('none');

  await act(async () => { b.resolve('B-only content'); await b.promise; });
  await waitFor(() => expect(screen.getByTestId('data').props.children).toBe('B-only content'));
});

it('discards a pending response after its screen unmounts', async () => {
  const a = deferred<string>();
  const request = jest.fn(() => a.promise);
  const screen = render(<Panel hotel="A" request={request} />);
  screen.unmount();
  await act(async () => { a.resolve('old content'); await a.promise; });
  expect(request).toHaveBeenCalledTimes(1);
});
